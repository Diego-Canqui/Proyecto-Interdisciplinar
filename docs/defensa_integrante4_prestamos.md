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
> - **Tablas en BD:** `prestamos`, `checklist`, `garantias`

---

## 1. Las 4 Preguntas Clave Básicas con sus Respuestas Exactas

### Pregunta 1: ¿Cuáles son las entidades de dominio y Value Objects de tu módulo y qué representan?
**Respuesta exacta:**
> *"Mi módulo implementa el Bounded Context de **Préstamos**, encargado de la transacción física real en ventanilla, custodia activa, verificación técnica y recepción de los recursos.*
>
> *Mis componentes clave de dominio son:*
> 1. **`Prestamo` (Aggregate Root):** Modela el contrato de posesión temporal del bien físico por parte del usuario. Contiene identificadores primitivos (`reserva_id`, `recurso_id`, `usuario_id`), fechas efectivas (`fecha_inicio`, `fecha_fin`) y su `estado: EstadoPrestamo`. Ofrece métodos de negocio como `iniciar()`, `devolver()`, `renovar()`, `vencer()` y `solicitar_prorroga()`.
> 2. **`Checklist` (Entidad interna del agregado):** Registra la inspección física detallada del equipo (estado de carcasa, pantalla, cargador, puertos, periféricos) en dos momentos críticos: inspección de entrega (salida) e inspección de recepción (retorno). Permite determinar objetivamente si el recurso sufrió daños.
> 3. **`Garantia` (Entidad interna del agregado):** Administra los documentos o depósitos en garantía retenidos como resguardo en préstamos de alto valor monetario o equipos de laboratorio especializado.
> 4. **`EstadoPrestamo` (Enum de dominio):**
>    - `ACTIVO`: Equipo en manos del usuario dentro del plazo pactado.
>    - `DEVUELTO`: Equipo reingresado a almacén tras inspección.
>    - `RENOVADO`: Plazo de devolución extendido conforme a las reglas.
>    - `VENCIDO` / `EN_MORA`: Superó la fecha máxima sin que el usuario haya hecho la entrega.*"

---

### Pregunta 2: ¿Cómo manejas la persistencia y quién hace el commit en tu esquema?
**Respuesta exacta:**
> *"La lógica de dominio de `Prestamo`, `Checklist` y `Garantia` es Python puro y no conoce nada de SQLAlchemy.*
>
> *La persistencia se implementa en la capa de infraestructura:*
> - *Mapeamos las entidades mediante modelos SQLAlchemy (`PrestamoModel`, `ChecklistModel`, `GarantiaModel`) configurados en el esquema `prestamos` de PostgreSQL (`__table_args__ = {"schema": "prestamos"}`).*
> - *El repositorio `SQLAlchemyPrestamoRepository` implementa la interfaz `PrestamoRepository`.*
> - *De acuerdo con el patrón **Unit of Work por petición HTTP (Decisión D13)**, el repositorio **NUNCA llama a `session.commit()`**, únicamente usa `session.flush()` para sincronizar y obtener identificadores autogenerados. El commit atómico lo ejecuta la dependencia compartida `shared.get_session` de FastAPI al concluir la petición exitosamente. Si ocurre algún error, se ejecuta el rollback automático evitando datos inconsistentes.*"

---

### Pregunta 3: ¿Cuáles son las reglas de negocio críticas que protege tu Aggregate Root?
**Respuesta exacta:**
> *"El Aggregate Root `Prestamo` protege las siguientes reglas del negocio:*
> 1. **Checklist obligatorio de salida:** Un préstamo no puede transicionar a estado `ACTIVO` si no cuenta con un `Checklist` de salida completado y firmado por el operador de almacén.
> 2. **Restricción de Renovación (`renovar`):** Un préstamo solo puede renovarse si se encuentra en estado `ACTIVO` (no en mora) y si ningún otro usuario tiene una reserva agendada sobre ese mismo recurso para las siguientes horas.
> 3. **Detección de Daños e Infracciones:** Al ejecutarse el método `devolver()`, el dominio compara el checklist de entrada contra el checklist inicial de salida. Si se detectan anomalías físicas o si la fecha actual sobrepasa `fecha_fin`, el caso de uso notifica de inmediato al contexto de Identidad para la penalización correspondiente.*"

---

### Pregunta 4: ¿Cómo te conectas con los otros contextos respetando DDD y el aislamiento arquitectónico?
**Respuesta exacta:**
> *"Nos conectamos mediante **bajo acoplamiento (Loose Coupling)** utilizando identificadores primitivos:*
> - ***Préstamos no importa modelos ni entidades ajenas:** En mi código está prohibido importar `UsuarioModel` o `RecursoModel`. Solo manipulo IDs primitivos (`UUID`).*
> - ***Orquestación en ventanilla (Capa de Aplicación):***
>   1. **Con Reservas:** Cuando el usuario llega al almacén, mi servicio de entrega recibe el `reserva_id`, comprueba que esté confirmada y solicita al módulo de Reservas marcarla como `CONVERTIDA`.
>   2. **Con Catálogo:** Una vez entregado el equipo, le solicito a Catálogo actualizar el recurso a `EN_USO`. Al devolverlo, si el checklist está conforme, le solicito marcarlo `DISPONIBLE`; si llegó averiado, le pido marcarlo `EN_MANTENIMIENTO`.
>   3. **Con Identidad:** Verifico la elegibilidad del usuario antes de la entrega. Al cerrar el préstamo, si la entrega fue puntual y en perfecto estado, invoco a Identidad para **sumar puntos de reputación** (`POST /reputacion/devoluciones-exitosas`); si hubo retraso o daño, invoco el registro de **sanción** (`POST /reputacion/sanciones`).*"

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
> 3. ***Autonomía del ciclo de vida:*** *Si el usuario nunca se presenta en la ventanilla, la reserva pasa a estado `VENCIDA` y el préstamo **jamás llega a existir**. Si hubiéramos reutilizado los mismos campos o la misma entidad, habríamos acoplado la intención teórica con la posesión física real, generando inconsistencias y perdiendo la auditoría del horario real de entrega y devolución."*

---

## 3. Cómo me comunico con mis otros 3 compañeros

| Compañero / Módulo | ¿Qué me pide él a mí? (Entrada) | ¿Qué le pido yo a él? (Salida) |
|---|---|---|
| **Persona 1 (Identidad)** | Identidad no me pide préstamos. | 1. Consulto si el `usuario_id` sigue siendo elegible en ventanilla.<br>2. Al devolver a tiempo: solicito **sumar reputación** (`POST /reputacion/devoluciones-exitosas`).<br>3. Al devolver tarde o con daños: solicito **aplicar sanción** (`POST /reputacion/sanciones`). |
| **Persona 2 (Catálogo)** | Catálogo no me pide préstamos. | 1. Al entregar el bien físico: solicito cambiar el estado del `recurso_id` a `EN_USO`.<br>2. Al recibir el bien en buen estado: solicito cambiar su estado a `DISPONIBLE`.<br>3. Al recibir el bien dañado: solicito cambiar su estado a `EN_MANTENIMIENTO` o `FUERA_DE_SERVICIO`. |
| **Persona 3 (Reservas)** | Reservas no me pide préstamos. | 1. Le envío el `reserva_id` para validar que la reserva esté en estado `CONFIRMADA` y vigente.<br>2. Al entregar el bien, le solicito cambiar el estado de la reserva a `CONVERTIDA`. |

---

## 4. Pitch de 10 Segundos

> [!TIP]
> **Si la profesora te pregunta de sorpresa: «¿Qué hace tu módulo de Préstamos y qué impacto tiene en todo el sistema?»**
>
> *"Mi módulo controla la **transacción física real del sistema en almacén**: formaliza la entrega y devolución del bien mediante checklists técnicos y garantías, asegurando que el inventario pase a `EN_USO` y alimentando el motor de reputación de Identidad con premios por puntualidad o sanciones por daños."*
