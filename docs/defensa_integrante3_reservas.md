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
>    - `PENDIENTE`: Solicitada en espera de validación de disponibilidad o elegibilidad.
>    - `CONFIRMADA`: Bloque temporal asegurado para el usuario.
>    - `CANCELADA`: Anulada por el usuario o administrador antes de su inicio.
>    - `VENCIDA`: Caducada por inasistencia del usuario en el tiempo de tolerancia pactado.
>    - `CONVERTIDA`: Exitosa, cuando el usuario se presenta en almacén y la reserva pasa a ser un préstamo físico activo.*"

---

### Pregunta 2: ¿Cómo manejas la persistencia y quién hace el commit en tu esquema?
**Respuesta exacta:**
> *"La entidad `Reserva` es una clase pura de Python. En la capa de infraestructura la mapeamos con SQLAlchemy a la base de datos PostgreSQL:*
> - *El modelo es `ReservaModel`, configurado con `__table_args__ = {"schema": "reservas"}` y tabla física `reservas.reservas`.*
> - *Persistimos a través de la implementación del repositorio `SQLAlchemyReservaRepository`.*
> - *En estricto apego al patrón **Unit of Work por petición HTTP (Decisión D13)**, el repositorio **NUNCA ejecuta `session.commit()`**. Solo utiliza `session.flush()` para sincronizar los cambios con la transacción abierta. Si la petición HTTP completa su flujo con éxito en FastAPI, la dependencia `shared.get_session` realiza el commit atómico; si algo falla, se dispara el rollback automático."*

---

### Pregunta 3: ¿Cuáles son las reglas de negocio críticas que protege tu Aggregate Root?
**Respuesta exacta:**
> *"El Aggregate Root `Reserva` protege las siguientes reglas del negocio:*
> 1. **Prevención de Solapamiento Temporal (Overbooking):** No pueden existir dos reservas activas (`CONFIRMADA`) para el mismo `recurso_id` cuya ventana temporal `[fecha_inicio, fecha_fin]` se intersecte. Esta verificación se realiza antes de persistir la confirmación.
> 2. **Validez del Rango Temporal:** `fecha_inicio` debe ser siempre menor que `fecha_fin` y debe programarse a futuro (no se pueden reservar fechas pasadas).
> 3. **Vigencia y Expiración Automática (`esta_vigente`):** Si el usuario no acude a reclamar su recurso dentro de una ventana de tolerancia tras `fecha_inicio` (ej. 15 minutos), el método de dominio marca la reserva como `VENCIDA`, liberando de inmediato el recurso para la comunidad.
> 4. **Transición hacia Préstamo (`convertir_a_prestamo`):** Solo una reserva en estado `CONFIRMADA` y vigente puede ser convertida. Una reserva `CANCELADA` o `VENCIDA` rechaza la conversión."*

---

### Pregunta 4: ¿Cómo te conectas con los otros contextos respetando DDD y el aislamiento arquitectónico?
**Respuesta exacta:**
> *"Nos conectamos respetando el principio de aislamiento estricto de Bounded Contexts en DDD:*
> - ***Referencias exclusivas por IDs primitivos:** Mi tabla `reservas.reservas` almacena `usuario_id: UUID` y `recurso_id: UUID`. No existen Foreign Keys en la base de datos hacia otros esquemas ni importaciones de modelos ORM de otros contextos.*
> - ***Validación previa en la Capa de Aplicación:** Cuando un usuario intenta crear una reserva:
>   1. Mi servicio de aplicación consulta a **Identidad** (`ConsultarElegibilidadUsuarioService`) enviando el `usuario_id`. Si el usuario está sancionado o tiene bajo puntaje, se rechaza la reserva.
>   2. Consulta a **Catálogo** enviando el `recurso_id` para confirmar que exista y no esté en mantenimiento o fuera de servicio.
>   3. Si ambas validaciones pasan, se crea la reserva y se le solicita a Catálogo marcar el estado del recurso como `RESERVADO`.*
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
| **Persona 1 (Identidad)** | Identidad no me pide reservas. | Le pido validar si el `usuario_id` que intenta reservar es **elegible para préstamo** (`es_elegible_para_prestamo`). Si tiene sanciones activas, no le permito reservar. |
| **Persona 2 (Catálogo)** | Catálogo no me pide reservas. | 1. Le pido verificar que el `recurso_id` esté en estado `DISPONIBLE`.<br>2. Al confirmar la reserva, le pido cambiar el estado del recurso a `RESERVADO`.<br>3. Si la reserva vence o se cancela, le pido liberar el recurso a `DISPONIBLE`. |
| **Persona 4 (Préstamos)** | Préstamos me envía el `reserva_id` al momento de la entrega física para verificar que esté `CONFIRMADA` y no vencida, y me pide transicionar su estado a `CONVERTIDA`. | Le entrego a Préstamos la reserva confirmada con sus datos (`usuario_id`, `recurso_id`, fechas) para que él inicie el préstamo físico. |

---

## 4. Pitch de 10 Segundos

> [!TIP]
> **Si la profesora te pregunta de sorpresa: «¿Qué resuelve el módulo de Reservas y cuál es su mayor valor técnico?»**
>
> *"Mi módulo resuelve la **planificación justa y eficiente de recursos compartidos**: previene matemáticamente el sobre-agendamiento (overbooking) en el tiempo, garantiza que solo usuarios con reputación intachable puedan apartar equipos y sincroniza de forma desacoplada la transición hacia el préstamo físico mediante identificadores primitivos."*
