# Guía de Defensa Individual — Integrante 2
## Contexto: Catálogo de Recursos

> [!IMPORTANT]
> **Ficha Técnica del Integrante**
> - **Rol:** Persona 2 — Responsable del Módulo de Catálogo
> - **Rama de Git:** `feature/catalogo`
> - **Bounded Context:** `catalogo`
> - **Carpeta Backend:** [`backend/src/prestamos_recursos/contexts/catalogo/`](file:///home/satome/Documentos/TI2/Proyecto/Proyecto-Interdisciplinar/backend/src/prestamos_recursos/contexts/catalogo)
> - **Carpeta Frontend:** [`frontend/src/features/catalogo/`](file:///home/satome/Documentos/TI2/Proyecto/Proyecto-Interdisciplinar/frontend/src/features/catalogo)
> - **Esquema de PostgreSQL:** `catalogo`
> - **Tablas en BD:** `recursos`

---

## 1. Las 4 Preguntas Clave Básicas con sus Respuestas Exactas

### Pregunta 1: ¿Cuáles son las entidades de dominio y Value Objects de tu módulo y qué representan?
**Respuesta exacta:**
> *"Mi módulo implementa el Bounded Context de **Catálogo**, encargado del inventario físico, categorización y estado operativo de todos los bienes institucionales.*
>
> *Mis componentes clave de dominio son:*
> 1. **`Recurso` (Aggregate Root):** Modela el recurso físico o digital (ej. laptop, proyector, microscopio). Sus atributos son `id: UUID`, `nombre: str`, `descripcion: str`, `categoria: str`, `estado: EstadoRecurso` y su `ficha_tecnica: FichaTecnica`.
> 2. **`FichaTecnica` (Value Object):** Objeto inmutable que agrupa las especificaciones técnicas del hardware: `marca`, `modelo`, `numero_serie` (identificador único de fábrica), `color`, `estado_fisico` y `foto_url`. Al ser un Value Object, se valida en su creación y no tiene identidad de ciclo de vida propia fuera del recurso.
> 3. **`EstadoRecurso` (Enum de dominio):** Define los estados formales del recurso:
>    - `DISPONIBLE`: Apto para ser reservado o prestado de inmediato.
>    - `EN_USO`: En posesión física de un usuario en un préstamo activo.
>    - `MANTENIMIENTO`: En revisión técnica (por ejemplo, cuando una devolución reporta daños).
>    - `FUERA_DE_SERVICIO`: Inoperativo o dado de baja definitiva.*"

---

### Pregunta 2: ¿Cómo manejas la persistencia y quién hace el commit en tu esquema?
**Respuesta exacta:**
> *"Mi entidad de dominio `Recurso` está completamente desacoplada de la base de datos (Python puro sin dependencias de SQLAlchemy ni FastAPI).*
>
> *La persistencia se implementa en la capa de infraestructura:*
> - *Mapeamos la entidad mediante el modelo ORM `RecursoModel` apuntando de forma explícita al esquema `catalogo` (`__table_args__ = {"schema": "catalogo"}`). La tabla física se llama `catalogo.recursos`.*
> - *El repositorio `SqlRecursoRepository` implementa la interfaz abstracta `RecursoRepository` definida en el dominio.*
> - *Siguiendo el patrón **Unit of Work por petición HTTP (Decisión D13 del proyecto)**, el repositorio **NUNCA hace `session.commit()`**, solo ejecuta `session.flush()` para registrar los cambios en la transacción activa. El commit definitivo lo hace la dependencia `shared.get_session` al finalizar la petición con éxito; como se inyecta con `Depends(get_session, scope="function")`, el commit se confirma antes de enviar la respuesta HTTP.*"

---

### Pregunta 3: ¿Cuáles son las reglas de negocio críticas que protege tu Aggregate Root?
**Respuesta exacta:**
> *"El Aggregate Root `Recurso` es el único responsable de salvaguardar la coherencia del estado del inventario:*
> 1. **Prohibición de disponibilidad de recursos dados de baja (`marcar_disponible`):** Si un recurso tiene el estado `FUERA_DE_SERVICIO`, el método `marcar_disponible()` lanza un `ValueError("No se puede marcar como disponible un recurso fuera de servicio.")`. Esto evita que un equipo inservible vuelva al flujo operativo por error humano o de interfaz.
> 2. **Transiciones controladas de disponibilidad (`marcar_no_disponible` y `actualizar_estado`):** Ningún agente externo puede mutar el estado con valores inválidos; el dominio valida que cualquier nuevo estado sea una instancia estricta de `EstadoRecurso`.
> 3. **Invarianza del número de serie:** El Value Object `FichaTecnica` exige `marca`, `modelo`, `numero_serie` y `estado_fisico` no vacíos (`es_valida()`), y la base de datos garantiza la unicidad del `numero_serie` con una restricción `UNIQUE`, para tener trazabilidad ante pérdidas o robos.*"

---

### Pregunta 4: ¿Cómo te conectas con los otros contextos respetando DDD y el aislamiento arquitectónico?
**Respuesta exacta:**
> *"Respetamos el aislamiento de Bounded Contexts mediante **Loose Coupling (Bajo Acoplamiento)**:*
> - ***Catálogo no conoce usuarios ni préstamos:** Mi código jamás importa `UsuarioModel` de Identidad ni `PrestamoModel` de Préstamos. Mi catálogo es agnóstico de quién solicita el bien.*
> - ***Paso de identificadores primitivos (`recurso_id: UUID`):** Cuando Préstamos necesita cambiar el estado de un recurso (a `EN_USO` al crear el préstamo, a `DISPONIBLE` o `MANTENIMIENTO` al devolverlo), lo hace con el `recurso_id` primitivo y el nuevo estado a través del contrato de repositorio de Catálogo (`RecursoRepository.actualizar_estado`). Hay que reconocer que ese acceso es una dependencia de código de `prestamos` hacia `catalogo`; los datos siguen cruzando solo por ID.*
> - ***Respuestas con DTOs planos:** Catálogo responde con DTOs de lectura serializados (`RecursoDTO`), conteniendo los datos necesarios para que el frontend o los otros módulos sepan si el recurso está libre.*"

---

### Pregunta 5: ¿El checklist de entrega depende del tipo de recurso?
**Respuesta exacta:**
> *"Hoy no. El checklist de salida del módulo de Préstamos tiene 4 casillas fijas (carcasa, pantalla, cables/cargador, nº de serie), pensadas para equipos de cómputo. Es una limitación conocida: la solución correcta es que Catálogo exponga en la ficha del recurso los criterios de inspección según su categoría (`Cómputo`, `Multimedia`, `Laboratorio`, `Libros`) y que Préstamos los renderice y los guarde de forma estructurada. Lo dejamos documentado como trabajo futuro entre Catálogo y Préstamos."*

---

## 2. La Pregunta Trampa de la Profesora (Nivel Senior)

> [!WARNING]
> **Pregunta Trampa:**
> *«Si un estudiante tiene una laptop prestada, ¿por qué en tu tabla `catalogo.recursos` no tienes una columna `usuario_actual_id` o `prestamo_actual_id` para saber rápidamente en la base de datos quién la tiene?»*

### Cómo responder como un desarrollador senior:
> *"Profesora, agregar `usuario_actual_id` en `catalogo.recursos` sería un **antipadrón grave de modelado que violaría el Principio de Responsabilidad Única y rompería la frontera de Bounded Contexts en DDD**.*
>
> *Las razones técnicas son:*
> 1. ***Diferente ciclo de vida y propósito:** El Bounded Context de Catálogo modela **inventario y especificaciones físicas estables** (¿qué es?, ¿cuál es su marca y serie?, ¿está operativo?). Saber quién lo tiene en este instante es una **relación transaccional efímera** que pertenece estrictamente al Bounded Context de **`prestamos`**.*
> 2. ***Acoplamiento innecesario:** Si pusiéramos `usuario_actual_id`, Catálogo tendría que manejar llaves foráneas o referencias a un concepto ajeno (`Usuario`), y obligaría a actualizar la tabla de Catálogo cada vez que un préstamo se cree, renueve o cancele.*
> 3. ***La solución limpia:** En Catálogo, el recurso simplemente refleja su estado objetivo: `estado = EN_USO`. Si alguien necesita saber los detalles de quién lo tiene, la interfaz de usuario o el servicio orquestador consulta al contexto de `prestamos` usando el `recurso_id`."*

---

## 3. Cómo me comunico con mis otros 3 compañeros

| Compañero / Módulo | ¿Qué me pide él a mí? (Entrada) | ¿Qué le pido yo a él? (Salida) |
|---|---|---|
| **Persona 1 (Identidad)** | Identidad no me pide recursos; sin embargo, yo verifico con el token JWT de Identidad que quien intente registrar o editar un recurso en el catálogo tenga rol `GESTOR_ALMACEN` o `ADMINISTRADOR_SISTEMA`. | **Nada.** Catálogo no consulta reputación ni perfiles. |
| **Persona 3 (Reservas)** | **Nada directo.** Reservas no consulta ni cambia el estado del recurso: el catálogo no tiene un estado «reservado»; la disponibilidad se valida al iniciar el préstamo. | **Nada.** Catálogo no consulta reservas. |
| **Persona 4 (Préstamos)** | 1. Verifica que el recurso exista y esté `DISPONIBLE` y lo pasa a `EN_USO` al crear el préstamo desde una reserva confirmada.<br>2. Al cancelar un préstamo `ACTIVO` en ventanilla, o al recibir el bien devuelto sin daños, me pide marcarlo `DISPONIBLE`; si llegó averiado, `MANTENIMIENTO`.<br>3. Mañana debería leer de mí los criterios de inspección del recurso para el checklist (tarea futura). | **Nada.** Catálogo no consulta detalles de préstamos ni garantías. |

---

## 4. Pitch de 10 Segundos

> [!TIP]
> **Si la profesora te pregunta de sorpresa: «¿Qué hace tu módulo de Catálogo y cuál es su responsabilidad principal?»**
>
> *"Mi módulo es el **custodio oficial del inventario institucional**: gestiona el alta, categorización, especificaciones técnicas inmutables y el ciclo de vida operativo de cada recurso (`DISPONIBLE`, `EN_USO`, `MANTENIMIENTO`, `FUERA_DE_SERVICIO`), protegiendo mediante reglas de dominio puras que jamás se pueda asignar un equipo fuera de servicio."*
