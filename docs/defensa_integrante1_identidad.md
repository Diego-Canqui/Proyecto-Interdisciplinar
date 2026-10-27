# Guía de Defensa Individual — Integrante 1 (Líder)
## Contexto: Identidad y Reputación

> [!IMPORTANT]
> **Ficha Técnica del Integrante**
> - **Rol:** Persona 1 — Líder de Proyecto & Arquitectura
> - **Rama de Git:** `feature/identidad-reputacion`
> - **Bounded Context:** `identidad_reputacion`
> - **Carpeta Backend:** [`backend/src/prestamos_recursos/contexts/identidad_reputacion/`](file:///home/satome/Documentos/TI2/Proyecto/Proyecto-Interdisciplinar/backend/src/prestamos_recursos/contexts/identidad_reputacion)
> - **Carpeta Frontend:** [`frontend/src/features/identidad/`](file:///home/satome/Documentos/TI2/Proyecto/Proyecto-Interdisciplinar/frontend/src/features/identidad)
> - **Esquema de PostgreSQL:** `identidad_reputacion`
> - **Tablas en BD:** `usuario`, `perfil_reputacion`, `sancion`, `excepcion_academica`

---

## 1. Las 4 Preguntas Clave Básicas con sus Respuestas Exactas

### Pregunta 1: ¿Cuáles son las entidades de dominio y Value Objects de tu módulo y qué representan?
**Respuesta exacta:**
> *"Mi bounded context está modelado mediante **Domain-Driven Design (DDD)** con dos subdominios fuertemente cohesionados: **Identidad** (gestión de acceso y credenciales) y **Reputación** (calificación dinámica del comportamiento de los usuarios).*
>
> *Mis componentes clave de dominio son:*
> 1. **`Usuario` (Aggregate Root de Identidad):** Representa a la persona física en el sistema. Modela su correo institucional validado, contraseña hasheada, estado activo y sus roles en el sistema (`ESTUDIANTE`, `DOCENTE`, `GESTOR_ALMACEN`, `ADMINISTRADOR_SISTEMA`). Contiene métodos puros como `activar()`, `desactivar()` y `tiene_rol()`.
> 2. **`PerfilReputacion` (Aggregate Root de Reputación):** Mantiene la salud de préstamo del usuario. Contiene su puntaje dinámico (`PuntajeReputacion`), nivel (`EXCELENTE`, `BUENO`, `REGULAR`, `CRITICO`), su colección de sanciones y excepciones académicas. Es la única entidad que decide si alguien es elegible con `es_elegible_para_prestamo()`.
> 3. **`Sancion` (Entidad interna de Reputación):** Modela penalizaciones por faltas (`LEVE`, `GRAVE`, `MUY_GRAVE`), fecha de aplicación, vigencia obligatoria (`fecha_fin NOT NULL`) y puntos descontados.
> 4. **`ExcepcionAcademica` (Entidad interna de Reputación):** Permite a un estudiante o docente levantar temporalmente bloqueos de sanciones para fines académicos o de investigación formal.
> 5. **Value Objects inmutables:** `PuntajeReputacion` (encapsula la lógica de suma/resta asegurando el rango estricto de [0, 1000] mediante *clamp*), `Email` y `PasswordHash`.*"

---

### Pregunta 2: ¿Cómo manejas la persistencia y quién hace el commit en tu esquema?
**Respuesta exacta:**
> *"Mis entidades de dominio son clases Python puras (sin SQLAlchemy ni dependencias de base de datos). La persistencia la resuelvo en la capa de infraestructura mediante mapeadores ORM (`UsuarioModel`, `PerfilReputacionModel`, `SancionModel`) que apuntan explícitamente al esquema `identidad_reputacion` de PostgreSQL.*
>
> *Implementamos el patrón **Unit of Work por petición HTTP (Decisión D13)**:*
> - *Mis repositorios (`SQLAlchemyUsuarioRepository`, `SQLAlchemyPerfilReputacionRepository`) y servicios de aplicación **NUNCA ejecutan `session.commit()`**; únicamente invocan `session.flush()` para sincronizar el estado y resolver IDs generados por la base de datos.*
> - *El **único dueño del commit** es la dependencia compartida `shared.get_session`. Al finalizar la petición HTTP con éxito, el generador ejecuta el commit de forma atómica. Si ocurre una excepción de dominio o un error 4xx/5xx, se ejecuta automáticamente un `session.rollback()`, garantizando consistencia total sin escrituras huérfanas.*"

---

### Pregunta 3: ¿Cuáles son las reglas de negocio críticas que protege tu Aggregate Root?
**Respuesta exacta:**
> *"El Aggregate Root `PerfilReputacion` protege tres invariantes críticas del negocio:*
> 1. **Elegibilidad estricta para préstamos (`es_elegible_para_prestamo`):** Un usuario queda automáticamente inhabilitado para solicitar recursos si tiene al menos una sanción activa (`fecha_fin > ahora`) o si su puntaje cayó a nivel `CRITICO` (< 200 puntos).
> 2. **Prevalencia de Excepciones Académicas:** Si el usuario tiene una sanción bloqueante pero cuenta con una `ExcepcionAcademica` vigente y no anulada, el método devuelve `True`, protegiendo la docencia e investigación sin borrar el historial punitivo.
> 3. **Topes de Puntaje y Amnistía:** El puntaje jamás puede ser menor a 0 ni superar 1000 (manejado por `PuntajeReputacion.sumar_con_tope`). Las sanciones vencidas se limpian automáticamente mediante un caso de uso de amnistía (`ejecutar_amnistia`), devolviendo al usuario a un estado hábil cuando cumple su periodo de castigo.*"

---

### Pregunta 4: ¿Cómo te conectas con los otros contextos respetando DDD y el aislamiento arquitectónico?
**Respuesta exacta:**
> *"Nos conectamos mediante **bajo acoplamiento (Loose Coupling)** y fronteras estrictas:*
> - ***Cero importaciones cruzadas:** En mi carpeta `contexts/identidad_reputacion/` está terminantemente prohibido importar modelos ORM, entidades o repositorios de `catalogo`, `reservas` o `prestamos`.*
> - ***Intercambio exclusivo por identificadores primitivos:** La comunicación inter-contexto se realiza únicamente enviando y recibiendo tipos primitivos (como `usuario_id: UUID`).*
> - ***Consumo mediante servicios de aplicación y endpoints:** Cuando el contexto de `prestamos` o `reservas` necesita verificar si un usuario puede operar, llama a mi endpoint `GET /reputacion/elegibilidad/{usuario_id}` o al servicio de aplicación `ConsultarElegibilidadUsuarioService`. Yo devuelvo un DTO plano booleano (`es_elegible: bool, motivo: str`), sin que ellos tengan que conocer mis tablas internas.*"

---

## 2. La Pregunta Trampa de la Profesora (Nivel Senior)

> [!WARNING]
> **Pregunta Trampa:**
> *«Si una sanción en tu tabla `sancion` es ocasionada porque el usuario devolvió tarde un equipo en el módulo de Préstamos, ¿por qué no le pusiste una clave foránea física en PostgreSQL del tipo `FOREIGN KEY (prestamo_id) REFERENCES prestamos.prestamo(id)`?»*

### Cómo responder como un desarrollador senior:
> *"Profesora, no creamos esa Foreign Key intencionalmente porque en **Domain-Driven Design y arquitecturas de microservicios / contextos delimitados, las claves foráneas entre esquemas rompen el aislamiento arquitectónico**.*
>
> *Si creáramos una `FOREIGN KEY` física entre `identidad_reputacion.sancion` y `prestamos.prestamo`:*
> 1. *Acoplaríamos las bases de datos a nivel de almacenamiento físico. Si mañana decidimos separar el contexto de Préstamos o Identidad a su propia base de datos o servidor independiente, la migración fallaría por la dependencia referencial.*
> 2. *Haríamos que el despliegue de tests unitarios y de integración de Identidad requiriera levantar e insertar datos falsos en las tablas de Préstamos.*
>
> *La solución arquitectónica correcta es la que implementamos: en `identidad_reputacion`, la sanción almacena el `motivo` y, si se requiere trazabilidad, un campo de referencia plano (`origen_referencia_id: UUID`) sin restricción de integridad foránea en la base de datos. La consistencia se valida en la capa de aplicación."*

---

## 3. Cómo me comunico con mis otros 3 compañeros

| Compañero / Módulo | ¿Qué me pide él a mí? (Entrada) | ¿Qué le pido yo a él? (Salida) |
|---|---|---|
| **Persona 2 (Catálogo)** | Validación de permisos/roles mediante JWT (ej. verificar si el usuario tiene rol `GESTOR_ALMACEN` o `ADMINISTRADOR_SISTEMA` para poder crear o editar recursos). | **Nada.** Identidad no depende del catálogo de recursos para operar usuarios ni reputaciones. |
| **Persona 3 (Reservas)** | Consulta de elegibilidad del usuario (`GET /reputacion/elegibilidad/{usuario_id}`) antes de aprobar o agendar una reserva de recurso. | **Nada.** Identidad no necesita consultar el estado de las reservas. |
| **Persona 4 (Préstamos)** | 1. Verificación de elegibilidad antes de entregar el equipo físico.<br>2. Reporte de eventos para ajustar reputación: notifica devoluciones a tiempo (`POST /reputacion/devoluciones-exitosas`) o infracciones/daños (`POST /reputacion/sanciones`). | **Nada.** Identidad solo expone sus contratos de aplicación; Préstamos es quien invoca a Identidad como consumidor. |

---

## 4. Pitch de 10 Segundos

> [!TIP]
> **Si la profesora te pregunta de sorpresa: «¿Qué hace exactamente tu módulo y por qué es el más crítico?»**
>
> *"Mi módulo gestiona la **identidad segura de los usuarios mediante JWT y Bcrypt**, y actúa como el **árbitro central del sistema mediante reputación dinámica**: calcula si un estudiante o docente tiene la calificación y habilitación requerida para retirar recursos, protegiendo al instituto de pérdidas mediante sanciones automáticas y excepciones académicas."*
