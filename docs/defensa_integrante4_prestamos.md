# Guía de Defensa Individual — Integrante 4
## Contexto: Préstamos y Devoluciones

> [!IMPORTANT]
> **Ficha Técnica del Integrante**
> - **Rol:** Persona 4 — Responsable del Módulo de Préstamos y Devoluciones
> - **Rama de Git:** `feature/prestamos`
> - **Bounded Context:** `prestamos`
> - **Carpeta Backend:** [`backend/src/prestamos_recursos/contexts/prestamos/`](file:///home/satome/Documentos/TI2/Proyecto/Proyecto-Interdisciplinar/backend/src/prestamos_recursos/contexts/prestamos)
> - **Carpeta Frontend:** [`frontend/src/features/prestamos/`](file:///home/satome/Documentos/TI2/Proyecto/Proyecto-Interdisciplinar/frontend/src/features/prestamos)
> - **Esquema de PostgreSQL:** `prestamos`
> - **Tablas en BD:** `prestamos`, `checklists`, `garantias`

---

## 1. Las 4 Preguntas Clave Básicas con sus Respuestas Exactas

### Pregunta 1: ¿Cuáles son las entidades de dominio y Value Objects de tu módulo y qué representan?
**Respuesta exacta:**
> *"Mi módulo implementa el Bounded Context de **Préstamos**, encargado de la transacción física real en ventanilla, custodia activa, verificación técnica y recepción de los recursos.*
>
> *Mis componentes clave de dominio son:*
> 1. **`Prestamo` (Aggregate Root):** Modela el contrato de posesión temporal del bien físico por parte del usuario. Contiene identificadores primitivos (`reserva_id`, `recurso_id`, `usuario_id`), fechas (`fecha_inicio`, `fecha_fin`, copiadas de la reserva al crearlo) y su `estado: EstadoPrestamo`. Ofrece métodos de negocio como `marcar_entregado()`, `devolver()`, `cancelar()`, `renovar()`, `vencer()` y `solicitar_prorroga()`.
> 2. **`Checklist` (Entidad interna del agregado):** Registra la inspección física del equipo (observaciones y fotos) en dos momentos: `ESTADO_INICIAL` (entrega) y `ESTADO_DEVOLUCION` (retorno). Hoy el frontend ofrece 4 casillas fijas (carcasa, pantalla, cables/cargador, nº de serie) que se guardan como texto en `observaciones`; hacerlas dinámicas según el recurso es trabajo futuro con Catálogo.
> 3. **`Garantia` (Entidad interna del agregado):** Administra la garantía que el usuario deja al recibir el bien (`CARNET_UNIVERSITARIO`, `DOCUMENTO_IDENTIDAD`, `DEPOSITO_ECONOMICO` u `OTRO`) junto con el Value Object `CompromisoResponsabilidad` (contenido, firma y testigo). Sus estados son `PENDIENTE` → `REGISTRADA`; `LIBERADA` y `RETENIDA` existen, pero `liberar()` y `retener()` aún no están implementados.
> 4. **`EstadoPrestamo` (Enum de dominio):**
>    - `ACTIVO`: Creado desde una reserva confirmada; el recurso ya está `EN_USO` y espera la entrega física en ventanilla.
>    - `ENTREGADO`: Garantía registrada y checklist de salida confirmado; el bien está en manos del usuario.
>    - `DEVUELTO`: Bien reingresado a almacén tras la inspección de retorno.
>    - `VENCIDO`: Superó `fecha_fin` sin devolverse.
>    - `CANCELADO`: Cancelado en ventanilla estando `ACTIVO`, sin penalizar la reputación.*"

---

### Pregunta 2: ¿Cómo manejas la persistencia y quién hace el commit en tu esquema?
**Respuesta exacta:**
> *"La lógica de dominio de `Prestamo`, `Checklist` y `Garantia` es Python puro y no conoce nada de SQLAlchemy.*
>
> *La persistencia se implementa en la capa de infraestructura:*
> - *Mapeamos las entidades mediante modelos SQLAlchemy (`PrestamoModel`, `ChecklistModel`, `GarantiaModel`) configurados en el esquema `prestamos` de PostgreSQL (`__table_args__ = {"schema": "prestamos"}`).*
> - *El repositorio `SqlPrestamoRepository` implementa la interfaz `PrestamoRepository`.*
> - *De acuerdo con el patrón **Unit of Work por petición HTTP (Decisión D13)**, el repositorio **NUNCA llama a `session.commit()`**, únicamente usa `session.flush()` para sincronizar y obtener identificadores autogenerados. El commit atómico lo ejecuta la dependencia compartida `shared.get_session` de FastAPI al concluir la petición exitosamente (inyectada con `scope="function"`, por lo que se confirma antes de enviar la respuesta). Si ocurre algún error, se ejecuta el rollback automático evitando datos inconsistentes.*"

---

### Pregunta 3: ¿Cuáles son las reglas de negocio críticas que protege tu Aggregate Root?
**Respuesta exacta:**
> *"El Aggregate Root `Prestamo` protege las siguientes reglas del negocio:*
> 1. **Entrega solo con checklist y garantía:** Un préstamo no pasa a `ENTREGADO` si no existe un `Checklist` `ESTADO_INICIAL` confirmado y una `Garantia` `REGISTRADA` con un compromiso válido (contenido, firma y testigo). Solo un préstamo `ACTIVO` puede entregarse o cancelarse en ventanilla.
> 2. **Restricción de Renovación (`renovar`):** Solo es apto un préstamo `ACTIVO` o `ENTREGADO`, con días > 0 y antes de `fecha_fin`; extiende 7 días. No comprueba reservas de otros usuarios, y el botón «+7 días» se retiró de la interfaz (Spec 006); el método y el endpoint se mantienen.
> 3. **Retrasos y daños al devolver:** `devolver()` calcula los días de retraso (fechas calendario en UTC) y el servicio registra el checklist de retorno; el gestor indica si hay daños. Con daños: `DANO_PARCIAL` (−30 pts) y el recurso pasa a `MANTENIMIENTO`; con retraso: `TARDANZA` (−10 pts; con 1 día solo puntos, desde 2 días bloqueo 1:1); puntual y sin daños: +10 pts.*"

---

### Pregunta 4: ¿Cómo te conectas con los otros contextos respetando DDD y el aislamiento arquitectónico?
**Respuesta exacta:**
> *"Nos conectamos mediante **bajo acoplamiento (Loose Coupling)** utilizando identificadores primitivos:*
> - ***Préstamos no importa modelos ni entidades ajenas:** En mi código está prohibido importar `UsuarioModel` o `RecursoModel`. Solo manipulo IDs primitivos (`UUID`).*
> - ***Orquestación en ventanilla (Capa de Aplicación):***
>   1. **Con Reservas:** Es Reservas quien me invoca: cuando gestión inicia el préstamo, `ReservaService.convertir_a_prestamo` llama a `PrestamoService.solicitar_prestamo` y luego marca su reserva `CONVERTIDA`. Yo solo guardo el `reserva_id`.
>   2. **Con Catálogo:** Al crear el préstamo verifico que el recurso exista y esté `DISPONIBLE`, y lo paso a `EN_USO`. Al devolver sin daños (o al cancelar un préstamo `ACTIVO`) lo libero a `DISPONIBLE`; si llegó averiado, lo paso a `MANTENIMIENTO`. Lo hago con `RecursoRepository.actualizar_estado`, que es una dependencia de código hacia `catalogo`.
>   3. **Con Identidad:** La elegibilidad del usuario se verifica antes de iniciar el préstamo (en `ReservaService`). Yo llamo a `ReputacionService`: `premiar_entrega_puntual` (+10) al entregar a tiempo, y al devolver `premiar_devolucion_puntual` (+10) o `aplicar_sancion` (`TARDANZA` / `DANO_PARCIAL`).*"

---

### Pregunta 5: ¿Cómo es el flujo de ventanilla actual (Spec 006)?
**Respuesta exacta:**
> *"Gestión inicia el préstamo desde una reserva `CONFIRMADA` y nace `ACTIVO`, con el recurso `EN_USO`. En `ACTIVO` solo hay dos acciones: **Realizar entrega** (garantía + checklist de salida con fotos → `ENTREGADO`, +10 pts si recogió a tiempo) o **Cancelar** (→ `CANCELADO`, recurso a `DISPONIBLE`, sin sanción). En `ENTREGADO` o `VENCIDO` solo está **Registrar devolución** (checklist de retorno, retraso y daños → `DEVUELTO`). Cancelar un préstamo ya entregado se rechaza con 409."*

---

## 2. La Pregunta Trampa de la Profesora (Nivel Senior)

> [!WARNING]
> **Pregunta Trampa:**
> *«Si la `Reserva` ya tenía una `fecha_inicio` y una `fecha_fin`, ¿por qué tu entidad `Prestamo` vuelve a tener campos `fecha_inicio` y `fecha_fin`? ¿No es eso duplicación y redundancia innecesaria de datos?»*

### Cómo responder como un desarrollador senior:
> *"Profesora, no es duplicación ni redundancia de datos: **son dos conceptos de negocio fundamentalmente distintos en momentos temporales diferentes**.*
>
> *La diferencia conceptual y técnica es:*
> 1. ***Reserva = Planificación / Intención futura:*** *La reserva modela una ventana estimada (ej. el usuario reservó el proyector de 10:00 AM a 12:00 PM).*
> 2. ***Préstamo = Realidad física efectiva:*** *El préstamo modela el momento exacto en que el recurso sale físicamente del almacén. El usuario pudo haber llegado a las 10:18 AM (esa es su `fecha_inicio` real) y se le pudo haber otorgado una prórroga autorizada hasta la 1:00 PM (su `fecha_fin` pactada de devolución).*
> 3. ***Autonomía del ciclo de vida:*** *Mientras gestión no inicie el préstamo, este **no existe**: la reserva puede cancelarse sin dejar rastros en `prestamos`. Si hubiéramos reutilizado la misma entidad, habríamos acoplado la intención teórica con la posesión física real.*
>
> *Para ser precisos: al crear el préstamo copiamos `fecha_inicio` y `fecha_fin` de la reserva, así que al inicio coinciden; después pueden diverger (por ejemplo, `renovar()` extiende `fecha_fin` del préstamo sin tocar la reserva). La entrega real queda reflejada en el estado `ENTREGADO` y en la fecha del checklist de salida. Una mejora pendiente es guardar la fecha real de devolución."*

---

## 3. Cómo me comunico con mis otros 3 compañeros

| Compañero / Módulo | ¿Qué me pide él a mí? (Entrada) | ¿Qué le pido yo a él? (Salida) |
|---|---|---|
| **Persona 1 (Identidad)** | Identidad no me pide préstamos. | 1. Al entregar a tiempo o devolver a tiempo sin daños: `premiar_entrega_puntual` / `premiar_devolucion_puntual` (+10 pts).<br>2. Al devolver tarde o con daños: `aplicar_sancion` (`TARDANZA` −10, `DANO_PARCIAL` −30).<br>3. Identidad me pide `contar_prestamos_en_curso` para el cupo de operaciones y la eliminación segura de usuarios. |
| **Persona 2 (Catálogo)** | Catálogo no me pide préstamos. | 1. Al crear el préstamo: verifico `DISPONIBLE` y lo paso a `EN_USO`.<br>2. Al devolver sin daños o cancelar un préstamo `ACTIVO`: `DISPONIBLE`.<br>3. Al devolver con daños: `MANTENIMIENTO`.<br>4. Futuro: leer de Catálogo los criterios de inspección del checklist. |
| **Persona 3 (Reservas)** | Reservas me invoca para crear el préstamo (`solicitar_prestamo`). | Nada directo: Reservas me invoca (`solicitar_prestamo`) y es ella quien marca la reserva `CONVERTIDA`. Identidad/Reservas me piden `contar_prestamos_en_curso`. |

---

## 4. Pitch de 10 Segundos

> [!TIP]
> **Si la profesora te pregunta de sorpresa: «¿Qué hace tu módulo de Préstamos y qué impacto tiene en todo el sistema?»**
>
> *"Mi módulo controla la **transacción física real del sistema en almacén**: formaliza la entrega y devolución del bien mediante checklists técnicos y garantías, asegurando que el inventario pase a `EN_USO` y alimentando el motor de reputación de Identidad con premios por puntualidad o sanciones por daños."*
