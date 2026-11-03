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
   - `ESTUDIANTE` y `DOCENTE`: Usuarios solicitantes. Pueden consultar el catálogo, solicitar reservas, cancelar sus propias reservas, ver sus préstamos/checklists y solicitar renovación.
   - `GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA`: Roles de gestión. Tienen acceso global a todas las reservas y préstamos, registran y actualizan recursos, confirman reservas pendientes, inician préstamos, formalizan entregas con garantía/checklist, procesan devoluciones y administran reputación, sanciones y excepciones académicas.

2. **Autenticación y credenciales:**
   - Contraseñas almacenadas únicamente como hash `bcrypt` (coste 12).
   - Sesiones mediante token JWT (`HS256`) firmado con `JWT_SECRET` del entorno y enviado en la cabecera `Authorization: Bearer <token>`.
   - Protección contra fuerza bruta mediante `slowapi` (rate limiting en login y registro).

---

## 5. Resumen del Flujo Completo entre los 4 Contextos

1. **Catálogo (`catalogo`):** El gestor registra el recurso con su ficha técnica y queda en estado `DISPONIBLE`.
2. **Reserva (`reservas`):** El usuario solicita reservar el recurso en un rango de fechas. Si el horario está libre, pasa directo a `CONFIRMADA`. Si está ocupado por otra reserva confirmada, entra en `PENDIENTE` (lista de espera ordenada de mayor a menor reputación consultando a `identidad_reputacion`).
3. **Inicio de Préstamo (`reservas` → `prestamos` → `catalogo`):** Cuando el usuario se presenta, el gestor inicia el préstamo desde la reserva confirmada. El préstamo nace en estado `ACTIVO` y el recurso pasa a `EN_USO`.
4. **Entrega Física (`prestamos` → `identidad_reputacion`):** En ventanilla, el gestor registra la `Garantia` (carné, DNI o depósito) y confirma el `Checklist` de salida. El préstamo pasa a `ENTREGADO`. Si el usuario recogió en la fecha pactada, recibe +10 puntos de reputación.
5. **Devolución (`prestamos` → `catalogo` + `identidad_reputacion`):** Al devolver el bien, el gestor registra el `Checklist` de retorno.
   - Si fue puntual y sin daños: el préstamo pasa a `DEVUELTO`, el recurso vuelve a `DISPONIBLE` y el usuario gana +15 puntos de reputación.
   - Si hubo retraso: se aplica sanción `TARDANZA` (-20 pts base y -5 pts por día de mora).
   - Si hubo daños físicos: se aplica sanción `DANO_PARCIAL` (-100 pts) y el recurso pasa automáticamente a `MANTENIMIENTO`.
