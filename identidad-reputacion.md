# Análisis Técnico: Contexto Identidad y Reputación

Este documento presenta el análisis técnico del código implementado en la rama `feature/identidad-reputacion`, evaluando el estado actual del contexto, sus dependencias con otros bounded contexts y los requerimientos necesarios para la integración con el contexto de **Catálogo** bajo los principios de Domain-Driven Design (DDD).

---

## 1. Estado del Contexto (`identidad_reputacion`)

El contexto de **Identidad y Reputación** se encuentra sólidamente implementado tanto en el backend (`backend/src/prestamos_recursos/contexts/identidad_reputacion/`) como en el frontend (`frontend/src/features/identidad/`). A continuación se detallan sus componentes:

### A. Entidades y Value Objects de Dominio
- **`Usuario` (Aggregate Root):** Gestiona la identidad del usuario, datos de contacto (`nombre`, `correo`, `telefono`), hash seguro de contraseña (`bcrypt`), estado operativo (`estado: bool`) y roles (`roles: list[RolUsuario]`).
- **`PerfilReputacion` (Aggregate Root):** Administra la reputación del usuario mediante valor de puntaje y nivel (`PuntajeReputacion`, `NivelReputacion`).
- **`Sancion` (Aggregate Root):** Registra sanciones aplicadas a perfiles de reputación (`TipoSancion`, puntos de descuento, monto, motivo, fecha).
- **`ExcepcionAcademica` (Aggregate Root):** Gestiona excepciones temporales para usuarios.
- **Value Objects / Enums:** `PuntajeReputacion`, `RolUsuario` (`ESTUDIANTE`, `DOCENTE`, `ADMINISTRADOR`, etc.), `TipoSancion`, `NivelReputacion`.

### B. Servicios de Aplicación
- **`AutenticacionService`:** Maneja el registro de usuarios (con validación de correo único y hashing de contraseñas), autenticación (`login`), emisión y validación de tokens JWT (`sub`, `roles`, expiración).
- **`UsuarioService`:** Operaciones CRUD de usuarios y listados.
- **`GestionAccesoService`:** Validaciones de acceso basadas en JWT y permisos (`autenticar_jwt`, `obtener_usuario_autenticado`).
- **`ReputacionService`:** Estructura base para la gestión de sanciones y reputación.

### C. Endpoints Expuestos (FastAPI)
Bajo los prefijos `/auth` y `/usuarios`:
- `POST /auth/registro` (201 Created): Registra un usuario y retorna token JWT + DTO de usuario (con protección de rate limiting).
- `POST /auth/login` (200 OK): Autentica credenciales y retorna token JWT.
- `POST /auth/logout` (200 OK): Cierre de sesión stateless.
- `GET /auth/perfil` (200 OK): Obtiene el perfil del usuario autenticado a partir del header `Authorization: Bearer <token>`.
- `POST /usuarios` (200 OK): Creación de usuario (rol administrativo).
- `GET /usuarios` (200 OK): Listado de usuarios registrados.

### D. Interfaz de Usuario (Frontend)
- `LoginPage.jsx`: Vista de inicio de sesión.
- `RegistroPage.jsx`: Vista de registro con validaciones robustas en cliente (email, teléfono, complejidad de contraseña).
- `UsuariosPage.jsx`: Gestión de usuarios.
- `api.js`: Cliente HTTP integrado con `apiClient`.

---

## 2. Dependencias Externas y Referencias a Catálogo

- **Aislamiento Actual:** En el código actual de la rama `feature/identidad-reputacion`, **no existen referencias directas** al `recurso_id` ni consultas sincrónicas al contexto de **Catálogo**. Esto es arquitectónicamente correcto bajo DDD, ya que Identidad y Reputación es un bounded context autónomo centrado en usuarios, credenciales y reputación.
- **Interacción Indirecta / Futura:** 
  - Las sanciones (`Sancion`) o reputación de un usuario pueden verse afectadas por incidentes relacionados con recursos (ej. daño o pérdida de un recurso del catálogo).
  - El contexto de Catálogo **dependerá** de los mecanismos de autenticación y autorización provistos por Identidad y Reputación (`GestionAccesoService`, dependencias de seguridad FastAPI `get_current_user`) para proteger sus operaciones de administración (creación y modificación de recursos).

---

## 3. Requerimientos para el Contexto de Catálogo

Para que el sistema funcione de manera integrada y armónica, respetando las reglas de DDD (comunicación desacoplada únicamente mediante identificadores únicos y servicios de aplicación), **se deben construir** en la carpeta `catalogo` (`backend/src/prestamos_recursos/contexts/catalogo/`) los siguientes componentes:

### A. Métodos de Servicio Interno (Application Layer)
Ubicación esperada: `backend/src/prestamos_recursos/contexts/catalogo/application/recurso_service.py`

1. **`crear_recurso(datos: CrearRecursoDTO) -> RecursoDTO`**
   - Registra un nuevo recurso con su ficha técnica y estado inicial `DISPONIBLE`.
2. **`obtener_recurso_por_id(id_recurso: UUID) -> RecursoDTO`**
   - Consulta un recurso por su ID. Lanza excepción controlada si no existe (para validaciones de otros contextos).
3. **`buscar_recursos(categoria: str | None, filtro: str | None) -> list[RecursoDTO]`**
   - Lista y filtra recursos del inventario.
4. **`consultar_disponibilidad(id_recurso: UUID) -> bool`**
   - Retorna `True` si el recurso existe y su estado permite ser reservado o prestado.
5. **`obtener_ficha_tecnica(id_recurso: UUID) -> FichaTecnicaDTO`**
   - Retorna las especificaciones técnicas inmutables del recurso.
6. **`actualizar_estado_recurso(id_recurso: UUID, nuevo_estado: EstadoRecurso) -> None`**
   - Modifica el estado operativo del recurso (ej. `DISPONIBLE`, `EN_USO`, `EN_MANTENIMIENTO`), útil para notificaciones desde Préstamos.

### B. Endpoints de FastAPI (Presentation Layer)
Ubicación esperada: `backend/src/prestamos_recursos/contexts/catalogo/presentation/recurso_controller.py` (Prefijo: `/recursos`)

1. **`POST /recursos`**
   - **Descripción:** Registra un nuevo recurso en el catálogo (requiere rol de administrador validado por `identidad_reputacion`).
2. **`GET /recursos`**
   - **Descripción:** Busca y lista recursos aplicando filtros opcionales de categoría o texto.
3. **`GET /recursos/{id_recurso}`**
   - **Descripción:** Obtiene los datos detallados de un recurso específico.
4. **`GET /recursos/{id_recurso}/disponibilidad`**
   - **Descripción:** Consulta si un recurso específico se encuentra disponible.
5. **`GET /recursos/{id_recurso}/ficha-tecnica`**
   - **Descripción:** Consulta la ficha técnica detallada del recurso.
6. **`PATCH /recursos/{id_recurso}/estado`**
   - **Descripción:** Actualiza el estado operativo del recurso.
