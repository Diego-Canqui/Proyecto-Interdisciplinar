# Guía de Defensa Individual — Integrante 3
## Contexto: Reservas

> [!IMPORTANT]
> **Ficha Técnica del Integrante**
> - **Rol:** Persona 3 — Responsable del Módulo de Reservas
> - **Rama de Git:** `feature/reservas`
> - **Bounded Context:** `reservas`
> - **Carpeta Backend:** [`backend/src/prestamos_recursos/contexts/reservas/`](file:///home/satome/Documentos/TI2/Proyecto/Proyecto-Interdisciplinar/backend/src/prestamos_recursos/contexts/reservas)
> - **Carpeta Frontend:** [`frontend/src/features/reservas/`](file:///home/satome/Documentos/TI2/Proyecto/Proyecto-Interdisciplinar/frontend/src/features/reservas)
> - **Esquema de PostgreSQL:** `reservas`
> - **Tablas en BD:** `reservas`

---

## 1. Las 4 Preguntas Clave Básicas con sus Respuestas Exactas

### Pregunta 1: ¿Cuáles son las entidades de dominio y Value Objects de tu módulo y qué representan?
**Respuesta exacta:**
> *"Mi módulo implementa el Bounded Context de **Reservas**, encargado de la planificación anticipada, asignación de turnos y franjas temporales para el uso de los recursos.*
>
> *Mis componentes clave de dominio son:*
> 1. **`Reserva` (Aggregate Root):** Modela la intención confirmada de uso de un recurso en un intervalo temporal específico. Sus atributos esenciales son:
>    - `id: UUID`: Identificador único de la reserva.
>    - `usuario_id: UUID`: Referencia al solicitante (tipo primitivo, sin acoplamiento a la entidad Usuario).
>    - `recurso_id: UUID`: Referencia al recurso solicitado (tipo primitivo, sin acoplamiento a la entidad Recurso).
>    - `fecha_inicio: datetime` y `fecha_fin: datetime`: Ventana temporal reservada (con zona horaria UTC).
>    - `estado: EstadoReserva`: Estado del ciclo de vida de la reserva.
> 2. **`EstadoReserva` (Enum de dominio):**
>    - `PENDIENTE`: En la **lista de espera**: otra reserva `CONFIRMADA` ocupa ese horario. Se ordena por reputación.
>    - `CONFIRMADA`: Bloque temporal asegurado. Si el horario está libre, la reserva nace directamente confirmada.
>    - `CANCELADA`: Anulada por el usuario o administrador antes de su inicio.
>    - `VENCIDA`: Existe en el enum, pero hoy ninguna tarea automática la asigna (limitación conocida).
>    - `CONVERTIDA`: Exitosa, cuando el usuario se presenta en almacén y la reserva pasa a ser un préstamo físico activo.*"

---

### Pregunta 2: ¿Cómo manejas la persistencia y quién hace el commit en tu esquema?
**Respuesta exacta:**
> *"La entidad `Reserva` es una clase pura de Python. En la capa de infraestructura la mapeamos con SQLAlchemy a la base de datos PostgreSQL:*
> - *El modelo es `ReservaModel`, configurado con `__table_args__ = {"schema": "reservas"}` y tabla física `reservas.reservas`.*
> - *Persistimos a través de la implementación del repositorio `SqlReservaRepository`.*
> - *En estricto apego al patrón **Unit of Work por petición HTTP (Decisión D13)**, el repositorio **NUNCA ejecuta `session.commit()`**. Solo utiliza `session.flush()` para sincronizar los cambios con la transacción abierta. Si la petición HTTP completa su flujo con éxito en FastAPI, la dependencia `shared.get_session` realiza el commit atómico; si algo falla, se dispara el rollback automático. Al inyectarla con `Depends(get_session, scope="function")`, el commit se confirma antes de enviar la respuesta, por lo que el frontend puede volver a listar y ver la reserva recién creada. Corregimos además que `SqlReservaRepository.guardar()` no hacía `flush()` como los demás repositorios."*

---

### Pregunta 3: ¿Cuáles son las reglas de negocio críticas que protege tu Aggregate Root?
**Respuesta exacta:**
> *"El Aggregate Root `Reserva` protege las siguientes reglas del negocio:*
> 1. **Prevención de Solapamiento Temporal (Overbooking):** No pueden existir dos reservas `CONFIRMADA` para el mismo `recurso_id` cuyas ventanas `[fecha_inicio, fecha_fin)` se intersecten (`se_superpone_con`; horarios consecutivos no chocan). Si el horario ya está ocupado, la nueva reserva queda `PENDIENTE` en la lista de espera; un mismo usuario no puede duplicar una reserva activa en el mismo horario (409).
> 2. **Validez del Rango Temporal:** `fecha_fin` debe ser posterior a `fecha_inicio` (`__post_init__`) y la duración máxima es de **7 días** (`Reserva.crear`, Spec 006). El formulario del frontend impide elegir fechas pasadas.
> 3. **Vigencia (`esta_vigente`):** Una reserva `PENDIENTE` o `CONFIRMADA` solo está vigente mientras `fecha_fin >= ahora`; la cola de espera y las promociones ignoran las reservas no vigentes. No hay una tolerancia de 15 minutos ni expiración automática.
> 4. **Transición hacia Préstamo (`convertir_a_prestamo`):** Solo una reserva `CONFIRMADA` puede convertirse en préstamo (`convertir_a_prestamo`), y solo la gestión puede iniciarla. Una reserva `CANCELADA`, `VENCIDA` o `CONVERTIDA` la rechaza."*

---

### Pregunta 4: ¿Cómo te conectas con los otros contextos respetando DDD y el aislamiento arquitectónico?
**Respuesta exacta:**
> *"Nos conectamos respetando el principio de aislamiento estricto de Bounded Contexts en DDD:*
> - ***Referencias exclusivas por IDs primitivos:** Mi tabla `reservas.reservas` almacena `usuario_id: UUID` y `recurso_id: UUID`. No existen Foreign Keys en la base de datos hacia otros esquemas ni importaciones de modelos ORM de otros contextos.*
> - ***Validación previa en la Capa de Aplicación:** Cuando un usuario intenta crear una reserva:
>   1. El controlador rechaza con 403 a quien tenga rol de gestión y a quien intente reservar para otro usuario.
>   2. Mi servicio de aplicación consulta a **Identidad** (`ReputacionService`, solo lectura) enviando el `usuario_id`: si tiene una sanción vigente no cubierta por excepción, rechaza con 409; además consulta su nivel para aplicar el cupo de operaciones simultáneas (BAJO 1, NORMAL 2, BUENO 3, EXCELENTE 5), sumando reservas activas y préstamos en curso.
>   3. Si el horario está libre, la reserva nace `CONFIRMADA`; si está ocupado, `PENDIENTE`. **No** consulto el estado del recurso en Catálogo ni lo modifico: esa validación ocurre al iniciar el préstamo.*
> - ***Consumo por parte de Préstamos:** Cuando el usuario llega a recoger el equipo, el módulo de Préstamos recibe el `reserva_id`, valida su estado `CONFIRMADA` y me solicita actualizarla a `CONVERTIDA`."*

---

## 2. La Pregunta Trampa de la Profesora (Nivel Senior)

> [!WARNING]
> **Pregunta Trampa:**
> *«Si una reserva depende críticamente de un usuario existente y de un recurso válido, ¿por qué no pusiste una Foreign Key relacional en PostgreSQL hacia `identidad_reputacion.usuario(id)` y hacia `catalogo.recursos(id)` para que la base de datos garantice la integridad referencial?»*

### Cómo responder como un desarrollador senior:
> *"Profesora, esa es una excelente pregunta conceptual. La razón por la que no pusimos esas Foreign Keys físicas en la base de datos es que **en Domain-Driven Design (DDD), los límites de un Bounded Context deben ser autónomos a nivel de infraestructura y persistencia**.*
>
> *Si creáramos esas dos Foreign Keys:*
> 1. ***Acoplaríamos el despliegue y los esquemas:*** *Cualquier cambio de esquema en Identidad o Catálogo podría bloquear las migraciones de Reservas. Además, si el sistema evoluciona a microservicios en bases de datos separadas, esas Foreign Keys colapsarían el sistema porque SQL no admite FKs entre servidores o bases de datos diferentes.*
> 2. ***Violación de la frontera de contexto:*** *El contexto de Reservas debe ser agnóstico del modelo interno de datos de Identidad y Catálogo.*
>
> *Por tanto, **la integridad referencial y la coherencia de negocio no se delegan ciegamente al motor de la base de datos, sino que se garantizan en la Capa de Aplicación (Application Services)** mediante validaciones explícitas antes de ejecutar la transacción."*

---

## 3. Cómo me comunico con mis otros 3 compañeros

| Compañero / Módulo | ¿Qué me pide él a mí? (Entrada) | ¿Qué le pido yo a él? (Salida) |
|---|---|---|
| **Persona 1 (Identidad)** | Identidad no me pide reservas. | Le pido la **elegibilidad** (sin sanciones vigentes no cubiertas), el **nivel** (cupo de operaciones) y el **puntaje** (orden de la cola) de cada `usuario_id`, con las consultas de solo lectura de `ReputacionService`. |
| **Persona 2 (Catálogo)** | Catálogo no me pide reservas. | **Nada.** No consulto ni cambio el estado del recurso; solo guardo su `recurso_id`. |
| **Persona 4 (Préstamos)** | Reservas es quien invoca a Préstamos: al convertir una reserva `CONFIRMADA` (acción de gestión) llamo a `PrestamoService.solicitar_prestamo` y, si todo sale bien, marco la reserva `CONVERTIDA`. | Le entrego los datos primitivos de la reserva (`reserva_id`, `usuario_id`, `recurso_id`, fechas) para que cree el préstamo `ACTIVO`. |

---

## 4. Pitch de 10 Segundos

> [!TIP]
> **Si la profesora te pregunta de sorpresa: «¿Qué resuelve el módulo de Reservas y cuál es su mayor valor técnico?»**
>
> *"Mi módulo resuelve la **planificación justa y eficiente de recursos compartidos**: previene matemáticamente el sobre-agendamiento (overbooking) en el tiempo, ordena la lista de espera por reputación, limita las operaciones simultáneas según el nivel y bloquea a los usuarios sancionados y sincroniza de forma desacoplada la transición hacia el préstamo físico mediante identificadores primitivos."*
