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
> - **Tablas en BD:** `usuario`, `perfiles_reputacion`, `sancion`, `excepciones_academicas`

---

## 1. Las 4 Preguntas Clave Básicas con sus Respuestas Exactas

### Pregunta 1: ¿Cuáles son las entidades de dominio y Value Objects de tu módulo y qué representan?
**Respuesta exacta:**
> *"Mi bounded context está modelado mediante **Domain-Driven Design (DDD)** con dos subdominios fuertemente cohesionados: **Identidad** (gestión de acceso y credenciales) y **Reputación** (calificación dinámica del comportamiento de los usuarios).*
>
> *Mis componentes clave de dominio son:*
> 1. **`Usuario` (Aggregate Root de Identidad):** Representa a la persona física en el sistema. Modela su correo institucional validado, contraseña hasheada, estado activo y sus roles en el sistema (`ESTUDIANTE`, `DOCENTE`, `PERSONAL_ADMINISTRATIVO`, `GESTOR_ALMACEN`, `ADMINISTRADOR_SISTEMA`). Contiene métodos puros como `cambiar_roles()`, `establecer_estado()` y `verificar_password()`.
> 2. **`PerfilReputacion` (Aggregate Root de Reputación):** Mantiene la salud de préstamo del usuario. Contiene su puntaje dinámico (`PuntajeReputacion`), nivel (`BAJO`, `NORMAL`, `BUENO`, `EXCELENTE`), y su colección de sanciones (las excepciones académicas se consultan aparte). Decide si alguien es elegible con `es_elegible_para_prestamo()` / `sancion_bloqueante()`.
> 3. **`Sancion` (Entidad interna de Reputación):** Modela penalizaciones por faltas (`TARDANZA`, `DANO_PARCIAL`, `DANO_TOTAL`, `INASISTENCIA_RESERVA`), fecha de aplicación, vigencia obligatoria (`fecha_fin NOT NULL`) y puntos descontados.
> 4. **`ExcepcionAcademica` (Entidad interna de Reputación):** Registrada por gestión, permite que un usuario siga operando pese a una sanción de `TARDANZA` o `INASISTENCIA_RESERVA` mientras la excepción esté vigente. Nunca cubre sanciones por daños.
> 5. **Value Objects inmutables:** `PuntajeReputacion` (encapsula la lógica de suma/resta asegurando el rango estricto de [0, 1000] mediante *clamp*).*"

---

### Pregunta 2: ¿Cómo manejas la persistencia y quién hace el commit en tu esquema?
**Respuesta exacta:**
> *"Mis entidades de dominio son clases Python puras (sin SQLAlchemy ni dependencias de base de datos). La persistencia la resuelvo en la capa de infraestructura mediante mapeadores ORM (`UsuarioModel`, `PerfilReputacionModel`, `SancionModel`) que apuntan explícitamente al esquema `identidad_reputacion` de PostgreSQL.*
>
> *Implementamos el patrón **Unit of Work por petición HTTP (Decisión D13)**:*
> - *Mis repositorios (`SqlUsuarioRepository`, `SqlPerfilReputacionRepository`) y servicios de aplicación **NUNCA ejecutan `session.commit()`**; únicamente invocan `session.flush()` para sincronizar el estado y resolver IDs generados por la base de datos.*
> - *El **único dueño del commit** es la dependencia compartida `shared.get_session`. Las dependencias de sesión usan `Depends(get_session, scope="function")`, de modo que el commit se confirma **antes** de enviar la respuesta HTTP (con el alcance por defecto FastAPI respondía primero y confirmaba después, y un `GET` inmediato podía no ver el dato). Al finalizar la petición con éxito, el generador ejecuta el commit de forma atómica. Si ocurre una excepción de dominio o un error 4xx/5xx, se ejecuta automáticamente un `session.rollback()`, garantizando consistencia total sin escrituras huérfanas.*"

---

### Pregunta 3: ¿Cuáles son las reglas de negocio críticas que protege tu Aggregate Root?
**Respuesta exacta:**
> *"El Aggregate Root `PerfilReputacion` protege tres invariantes críticas del negocio:*
> 1. **Elegibilidad estricta para préstamos (`es_elegible_para_prestamo`):** Un usuario queda inhabilitado para operar si tiene al menos una sanción vigente (`activa` y `fecha_fin > ahora`) no cubierta por una excepción. El nivel de reputación **no** bloquea: solo fija la prioridad en la cola de espera y el cupo de operaciones simultáneas (BAJO 1, NORMAL 2, BUENO 3, EXCELENTE 5).
> 2. **Prevalencia de Excepciones Académicas:** Si el usuario tiene una sanción bloqueante de tipo `TARDANZA` o `INASISTENCIA_RESERVA` pero cuenta con una `ExcepcionAcademica` vigente y no anulada, el método devuelve `True` sin borrar el historial punitivo. Las sanciones por daños no se pueden cubrir.
> 3. **Topes de Puntaje y Amnistía:** El puntaje jamás puede ser menor a 0 ni superar 1000 (manejado por `PuntajeReputacion.sumar_con_tope`). Las sanciones dejan de bloquear solas cuando llega su `fecha_fin`, y la amnistía mensual (`ejecutar_amnistia_mensual`) suma +25 puntos a los perfiles en nivel `BAJO` sin sanciones en los últimos 30 días.*"

---

### Pregunta 4: ¿Cómo te conectas con los otros contextos respetando DDD y el aislamiento arquitectónico?
**Respuesta exacta:**
> *"Nos conectamos mediante **bajo acoplamiento (Loose Coupling)** y fronteras estrictas:*
> - ***Cero importaciones cruzadas:** En mi carpeta `contexts/identidad_reputacion/` está terminantemente prohibido importar modelos ORM, entidades o repositorios de `catalogo`, `reservas` o `prestamos`.*
> - ***Intercambio exclusivo por identificadores primitivos:** La comunicación inter-contexto se realiza únicamente enviando y recibiendo tipos primitivos (como `usuario_id: UUID`).*
> - ***Consumo mediante servicios de aplicación y endpoints:** Cuando el contexto de `prestamos` o `reservas` necesita verificar si un usuario puede operar, llama a mi servicio de aplicación `ReputacionService` (`obtener_elegibilidad`, o `consultar_elegibilidad_lectura` / `consultar_nivel_lectura` / `consultar_puntaje_lectura` cuando solo debe leer sin crear perfiles). Yo devuelvo un DTO plano (`ElegibilidadDTO`: `elegible: bool`, `razon: str`), sin que ellos tengan que conocer mis tablas internas. Además, el endpoint `GET /reputacion/elegibilidad` permite al usuario consultar la suya.*"

---

### Pregunta 5: ¿Qué se agregó con la Spec 006 (segregación de funciones y administración de usuarios)?
**Respuesta exacta:**
> *"Cuatro reglas: (1) **Segregación de funciones:** `GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA` operan el sistema pero no pueden solicitar reservas para sí mismos (403). (2) **Alta jerárquica:** el gestor solo crea roles solicitantes; el administrador crea cualquiera de los 5. (3) **Administración de cuentas** (solo administrador): cambiar rol, activar/desactivar y eliminar, con autoprotección (409) para no degradarse, desactivarse ni eliminarse a sí mismo; eliminar un usuario con reservas activas o préstamos en curso también da 409. (4) **Cuentas inactivas:** 403 tanto en el login como con un token emitido antes. Además, el nivel de reputación fija el cupo de operaciones simultáneas (BAJO 1, NORMAL 2, BUENO 3, EXCELENTE 5)."*

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
> *La solución arquitectónica correcta es la que implementamos: en `identidad_reputacion`, la sanción almacena el `motivo` (por ejemplo, «Devolución tardía») y los datos de la sanción, sin ninguna restricción de integridad foránea hacia otro esquema. Hoy no guarda un `prestamo_id`; si se requiriera trazabilidad, se añadiría como un UUID plano sin FK y la consistencia se validaría en la capa de aplicación."*

---

## 3. Cómo me comunico con mis otros 3 compañeros

| Compañero / Módulo | ¿Qué me pide él a mí? (Entrada) | ¿Qué le pido yo a él? (Salida) |
|---|---|---|
| **Persona 2 (Catálogo)** | Validación de permisos/roles mediante JWT (`get_current_user`, `require_roles`). | **Nada.** Identidad no depende del catálogo de recursos para operar usuarios ni reputaciones. |
| **Persona 3 (Reservas)** | Consulta de elegibilidad, nivel (cupo de operaciones: 1/2/3/5) y puntaje (orden de la cola de espera) mediante `ReputacionService`, antes de crear, confirmar o convertir una reserva. | **Nada.** Identidad no necesita consultar el estado de las reservas. |
| **Persona 4 (Préstamos)** | 1. Premios por puntualidad (`premiar_entrega_puntual`, `premiar_devolucion_puntual`: +10 pts cada uno).<br>2. Sanciones al devolver (`aplicar_sancion`): `TARDANZA` (−10) o `DANO_PARCIAL` (−30). | **Nada.** Identidad solo expone sus contratos de aplicación; Préstamos es quien invoca a Identidad como consumidor. |

---

## 4. Pitch de 10 Segundos

> [!TIP]
> **Si la profesora te pregunta de sorpresa: «¿Qué hace exactamente tu módulo y por qué es el más crítico?»**
>
> *"Mi módulo gestiona la **identidad segura de los usuarios mediante JWT y Bcrypt**, y actúa como el **árbitro central del sistema mediante reputación dinámica**: calcula si un estudiante o docente tiene la calificación y habilitación requerida para retirar recursos, protegiendo al instituto de pérdidas mediante sanciones automáticas y excepciones académicas."*
