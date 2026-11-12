# Políticas Generales del Sistema y Reparto del Proyecto

Este documento resume la distribución de responsabilidades por integrante y las políticas generales de arquitectura, seguridad y persistencia que rigen todo el sistema de Préstamos de Recursos.

## 1. Reparto del equipo por Bounded Context

| Integrante | Bounded Context (Backend) | Módulo Frontend | Schema en PostgreSQL |
|---|---|---|---|
| **Diego Canqui** | `identidad_reputacion` | `frontend/src/features/identidad/` | `identidad_reputacion` |
| **Rodrigo** | `catalogo` | `frontend/src/features/catalogo/` | `catalogo` |
| **Johan** | `reservas` | `frontend/src/features/reservas/` | `reservas` |
| **Diego Villanueva** | `prestamos` | `frontend/src/features/prestamos/` | `prestamos` |

Cada integrante cuenta con su propio documento detallado en esta carpeta:
- [`01_identidad_reputacion.md`](./01_identidad_reputacion.md)
- [`02_catalogo_rodrigo.md`](./02_catalogo_rodrigo.md)
- [`03_reservas_johan.md`](./03_reservas_johan.md)
- [`04_prestamos_diego.md`](./04_prestamos_diego.md)

---

## 2. Políticas de Arquitectura (DDD)

1. **Separación en 4 capas por contexto:**
   Cada contexto dentro de `backend/src/prestamos_recursos/contexts/<contexto>/` se divide estrictamente en:
   - `domain/`: Entidades, Value Objects, Enums, interfaces de repositorios y servicios de dominio.
   - `application/`: Servicios de casos de uso y DTOs (`dto/`).
   - `infrastructure/`: Modelos ORM de SQLAlchemy (`models/`) e implementaciones SQL de repositorios (`repositories/`).
   - `presentation/`: Controladores FastAPI (`APIRouter`) e inyección de dependencias.

2. **Regla de Dominio Puro:**
   La capa `domain/` solo contiene código Python estándar. No importa `fastapi`, `sqlalchemy`, `pydantic` ni módulos de `infrastructure/`.

3. **Aislamiento entre Bounded Contexts:**
   - Un contexto nunca importa entidades de dominio ni modelos ORM de otro contexto.
   - Las referencias entre contextos se hacen exclusivamente por identificador (`usuario_id: UUID`, `recurso_id: UUID`, `reserva_id: UUID`).
   - Cuando un caso de uso necesita operar sobre otro contexto (por ejemplo, `prestamos` premiando o sancionando la reputación al devolver un equipo, o `reservas` consultando el puntaje de reputación para ordenar la cola), lo hace a través del servicio de la capa `application/` del otro contexto.
   - En PostgreSQL, cada contexto tiene su propio schema aislado (`db/init.sql`), sin `JOIN` cruzados entre schemas.

---

## 3. Política de Transacciones en Base de Datos (Decisión D13)

- **Único dueño de la transacción:** El generador `get_session` en `backend/src/prestamos_recursos/shared/database.py` es el único responsable de hacer `session.commit()` al finalizar con éxito una petición HTTP y `session.rollback()` si ocurre cualquier excepción.
- **Repositorios sin commit:** Todos los repositorios SQL (`SqlUsuarioRepository`, `SqlPerfilReputacionRepository`, `SqlRecursoRepository`, `SqlReservaRepository`, `SqlPrestamoRepository`, etc.) utilizan `session.flush()` en lugar de `session.commit()`.
- **Por qué existe esta política:** Garantiza atomicidad cuando una petición coordina varios cambios (por ejemplo, al devolver un préstamo con daños se actualiza el préstamo a `DEVUELTO`, se guarda el checklist de retorno, se cambia el recurso a `MANTENIMIENTO` y se registra una sanción en la reputación del usuario; si cualquiera de esos pasos falla, se revierte toda la operación).

---

## 4. Políticas Transversales de Seguridad y Roles

1. **Roles del sistema (`RolUsuario`):**
   - `ESTUDIANTE`, `DOCENTE` y `PERSONAL_ADMINISTRATIVO`: Usuarios solicitantes. Pueden consultar el catálogo, solicitar reservas, cancelar sus propias reservas, ver sus préstamos/checklists y consultar su reputación personal.
   - `GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA`: Roles de gestión. Tienen acceso global a todas las reservas y préstamos, registran y actualizan recursos, confirman reservas pendientes, inician préstamos, formalizan entregas con garantía/checklist, cancelan préstamos no recogidos en ventanilla, procesan devoluciones y administran reputación, sanciones y excepciones académicas.
   - **Segregación de funciones (Spec 006):** `GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA` operan el sistema pero **no pueden solicitar reservas ni préstamos para sí mismos** (`403 Forbidden`). Además, `GESTOR_ALMACEN` solo puede crear usuarios con roles solicitantes (`ESTUDIANTE`, `DOCENTE`, `PERSONAL_ADMINISTRATIVO`), mientras que `ADMINISTRADOR_SISTEMA` puede crear usuarios con cualquiera de los 5 roles, cambiar roles (`PATCH /usuarios/{id}/rol`), activar/desactivar cuentas (`PATCH /usuarios/{id}/estado`) y eliminar usuarios sin operaciones activas (`DELETE /usuarios/{id}`), con reglas de autoprotección (`409 Conflict`) para no auto-degradarse, auto-desactivarse ni auto-eliminarse.

2. **Autenticación y credenciales:**
   - Contraseñas almacenadas únicamente como hash `bcrypt` (coste 12).
   - Sesiones mediante token JWT (`HS256`) firmado con `JWT_SECRET` del entorno y enviado en la cabecera `Authorization: Bearer <token>`.
   - Cuentas inactivas (`estado = False`): rechazadas con código `403 Forbidden` (`"La cuenta de usuario está desactivada"`) tanto al iniciar sesión en `/auth/login` como al verificar cualquier petición autenticada con token previo en `get_current_user` (Spec 006).
   - Protección contra fuerza bruta mediante `slowapi` (rate limiting en login y registro).

---

## 5. Resumen del Flujo Completo entre los 4 Contextos

1. **Catálogo (`catalogo`):** El gestor registra el recurso con su ficha técnica y queda en estado `DISPONIBLE`. Puede pasar a `EN_USO` al prestarse, a `MANTENIMIENTO` si se detectan daños o a `FUERA_DE_SERVICIO` si es dado de baja.
2. **Reserva (`reservas`):** El usuario solicita reservar un recurso.
   - **Políticas operativas (Spec 007):**
     - El recurso debe encontrarse en estado `DISPONIBLE` o `EN_USO` (se rechaza con `409 Conflict` si está en `MANTENIMIENTO` o `FUERA_DE_SERVICIO`, estado verificado vía `RecursoApplicationService`).
     - Horario de atención institucional: entregas y devoluciones únicamente de lunes a viernes entre las **08:00 y las 20:00 UTC** inclusive (`Reserva.crear`).
     - Duración: mínimo **1 hora** y máximo **7 días**.
     - Anticipación: no se permiten reservas en el pasado (con tolerancia de 5 minutos para desfases de reloj) y máximo **30 días** de anticipación respecto a la fecha de inicio.
     - Cupo y elegibilidad: rol solicitante (`403` para roles de gestión), sin sanciones bloqueantes activas (`409`) y respetando el cupo máximo de operaciones simultáneas según su `NivelReputacion` (`BAJO`: 1, `NORMAL`: 2, `BUENO`: 3, `EXCELENTE`: 5) sumando reservas activas y préstamos en curso.
   - Si el horario está libre, la reserva pasa directo a `CONFIRMADA`. Si se cruza con otra confirmada, queda en `PENDIENTE` (lista de espera ordenada de mayor a menor reputación). Al cancelarse una reserva confirmada, se promueve automáticamente al mejor candidato elegible sin sanciones.
3. **Inicio de Préstamo (`reservas` → `prestamos` → `catalogo`):**
   - El préstamo solo puede iniciarse dentro de la ventana operativa de conversión: **`fecha_inicio - 1 hora <= ahora <= fecha_fin`** (`409 Conflict` fuera de ventana).
   - El gestor inicia el préstamo desde la reserva confirmada (verificando que el titular no tenga sanción bloqueante activa sobrevenida). El préstamo nace en estado `ACTIVO` y el recurso pasa a `EN_USO` en catálogo.
4. **Entrega Física y Cancelación en Ventanilla (`prestamos` → `catalogo` + `identidad_reputacion`):** Mientras el préstamo está en estado `ACTIVO` (antes de la entrega física), el gestor puede:
   - **Completar la entrega:** Registra la `Garantia` (carné, DNI o depósito, en estado `REGISTRADA`) y el `Checklist` de salida (`ESTADO_INICIAL`). El préstamo pasa a `ENTREGADO`. Si el usuario recogió en o antes de la fecha pactada, recibe **+10 puntos** de reputación (`premiar_entrega_puntual`).
   - **Cancelar el préstamo en ventanilla (`POST /prestamos/{id}/cancelar`, Spec 006):** Si el solicitante no se presenta o desiste antes de la entrega física, el gestor cancela el préstamo. El préstamo pasa a `CANCELADO` y el recurso vuelve inmediatamente a `DISPONIBLE` en el catálogo sin penalizar la reputación del usuario.
5. **Devolución (`prestamos` → `catalogo` + `identidad_reputacion`):** Solo se habilita en ventanilla para préstamos en estado `ENTREGADO` o `VENCIDO`. Al devolver el bien, el gestor registra el `Checklist` de retorno (`ESTADO_DEVOLUCION`).
   - **Ciclo de vida de la Garantía (Spec 007):** Si `danos_detectados == False`, la garantía asociada pasa automáticamente a `LIBERADA` (registrando `fecha_liberacion`, visible en inspecciones); si `danos_detectados == True`, la garantía pasa a `RETENIDA`.
   - **Puntual y sin daños:** El préstamo pasa a `DEVUELTO`, el recurso vuelve a `DISPONIBLE` y el usuario gana **+10 puntos** de reputación (`premiar_devolucion_puntual`).
   - **Retraso en la entrega:** Se aplica sanción `TARDANZA` (-10 puntos, deuda $0, gracia de 1 día: si el retraso es ≤ 1 día no hay bloqueo; a partir del segundo día, bloqueo 1:1 en días).
   - **Daños físicos:** Se aplica sanción `DANO_PARCIAL` (-30 puntos, deuda $50, bloqueo de 30 días) o `DANO_TOTAL` (-100 puntos, deuda = valor del recurso, bloqueo de 60 días), pasando el recurso automáticamente a `MANTENIMIENTO` o `FUERA_DE_SERVICIO`.
   - **Inasistencia a reserva:** Sanción `INASISTENCIA_RESERVA` (-15 puntos, deuda $0, bloqueo fijo de 3 días).

