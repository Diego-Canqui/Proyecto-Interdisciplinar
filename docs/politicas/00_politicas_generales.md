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
- **El `commit` ocurre antes de responder:** Todas las dependencias que inyectan la sesión usan `Depends(get_session, scope="function")`. Con el alcance por defecto (`request`) FastAPI enviaba la respuesta `201`/`200` al navegador *antes* de ejecutar el `commit`, y un `GET` inmediato (por ejemplo, recargar la lista de reservas tras crear una) podía no ver aún el dato. Con `scope="function"` el `commit` se confirma antes de enviar la respuesta.
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

1. **Catálogo (`catalogo`):** El gestor registra el recurso con su ficha técnica y queda en estado `DISPONIBLE`.
2. **Reserva (`reservas`):** El usuario solicita reservar el recurso en un rango de fechas. Debe tener rol solicitante (`403` si tiene rol de gestión), no tener sanción bloqueante activa (`409`), no superar su cupo de operaciones activas simultáneas según su `NivelReputacion` (`BAJO`: 1, `NORMAL`: 2, `BUENO`: 3, `EXCELENTE`: 5) sumando reservas activas y préstamos en curso, y la duración máxima de toda reserva es de **7 días** (`409` si se supera). Si el horario está libre, pasa directo a `CONFIRMADA`. Si está ocupado por otra reserva confirmada, entra en `PENDIENTE` (lista de espera ordenada de mayor a menor reputación consultando a `identidad_reputacion`). Al cancelar una reserva confirmada, la cola promueve al mejor candidato saltando a quienes tengan sanciones activas.
3. **Inicio de Préstamo (`reservas` → `prestamos` → `catalogo`):** Cuando el usuario se presenta, el gestor inicia el préstamo desde la reserva confirmada (verificando que el titular no tenga sanción bloqueante activa sobrevenida). El préstamo nace en estado `ACTIVO` y el recurso pasa a `EN_USO`.
4. **Entrega Física y Cancelación en Ventanilla (`prestamos` → `catalogo` + `identidad_reputacion`):** Mientras el préstamo está en estado `ACTIVO` (antes de la entrega física), el gestor puede:
   - **Completar la entrega:** Registra la `Garantia` (carné, DNI o depósito) y el `Checklist` de salida con fotos. El préstamo pasa a `ENTREGADO`. Si el usuario recogió en la fecha pactada, recibe +10 puntos de reputación.
   - **Cancelar el préstamo en ventanilla (`POST /prestamos/{id}/cancelar`, Spec 006):** Si el solicitante no se presenta o desiste antes de la entrega física, el gestor cancela el préstamo. El préstamo pasa a `CANCELADO` y el recurso vuelve inmediatamente a `DISPONIBLE` en el catálogo sin penalizar la reputación del usuario.
5. **Devolución (`prestamos` → `catalogo` + `identidad_reputacion`):** Solo se habilita en ventanilla para préstamos en estado `ENTREGADO` o `VENCIDO`. Al devolver el bien, el gestor registra el `Checklist` de retorno.
   - Si fue puntual y sin daños: el préstamo pasa a `DEVUELTO`, el recurso vuelve a `DISPONIBLE` y el usuario gana +10 puntos de reputación.
   - Si hubo retraso (por días calendario en UTC): se aplica sanción `TARDANZA` (−10 pts). Con 1 día de retraso solo descuenta puntos (gracia de 1 día); desde 2 días de retraso bloquea 1 día por cada día de retraso.
   - Si hubo daños físicos: se aplica sanción `DANO_PARCIAL` (−30 pts, deuda de $50, 30 días de bloqueo) y el recurso pasa automáticamente a `MANTENIMIENTO`. `DANO_TOTAL` (−100 pts, 60 días) la registra gestión manualmente.
   - Si no asistió a recoger una reserva confirmada: sanción `INASISTENCIA_RESERVA` (−15 pts, 3 días), registrada manualmente por gestión (`POST /reputacion/sanciones`).

---

## 6. Limitaciones Conocidas y Trabajo Futuro

1. **Checklist de inspección fijo (pendiente para `catalogo` + `prestamos`):** El formulario de entrega de `/historial` muestra siempre las mismas 4 casillas (carcasa, pantalla, cables/cargador y nº de serie), sin importar el tipo de recurso. Lo correcto es que `catalogo` exponga los criterios de inspección según la categoría del recurso y que `prestamos` los muestre y los guarde de forma estructurada (hoy se guardan concatenados en `observaciones`). Para demostrar el flujo actual se usa un recurso de tipo cómputo (la *Laptop Dell Latitude 5420* del seed).
2. **Dependencias entre contextos por código:** Aunque las referencias de datos son solo por ID y los servicios se inyectan, `prestamos` importa `RecursoRepository`/`EstadoRecurso` de `catalogo` y `TipoSancion` de `identidad_reputacion`, y `reservas` importa `PrestamoService` y `NivelReputacion`. Es un desvío de la regla de aislamiento total que debe saberse al defender la arquitectura.
3. **Sanciones automáticas parciales:** Solo `TARDANZA` y `DANO_PARCIAL` se aplican automáticamente al devolver; `INASISTENCIA_RESERVA` y `DANO_TOTAL` son manuales. Las reservas `CONFIRMADA` no expiran por sí solas (`VENCIDA` existe en el enum pero no hay tarea que la asigne).
4. **Cálculo de retraso en UTC:** `calcular_dias_retraso` compara fechas en UTC, no en hora local; una devolución cerca de la medianoche local puede contar un día de más.

