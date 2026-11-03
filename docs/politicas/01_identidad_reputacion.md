# Contexto 1: Identidad y Reputación (`identidad_reputacion`)

**Responsable:** Integrante 1 (Diego Canqui)  
**Backend:** `backend/src/prestamos_recursos/contexts/identidad_reputacion/`  
**Frontend:** `frontend/src/features/identidad/`  
**Schema BD:** `identidad_reputacion`

---

## 1. Qué se implementó en este contexto

1. **Registro e inicio de sesión seguro:**
   - Creación de usuarios con validación de fortaleza de contraseña (mínimo 8 caracteres, mayúscula, minúscula y dígito), correo único y asignación de rol inicial (`ESTUDIANTE` por defecto) y perfil de reputación en 500 puntos.
   - Autenticación con `bcrypt` y emisión de token JWT (`HS256`) que incluye el `sub` (ID del usuario) y la lista de `roles`.
   - Rate limiting en los endpoints de autenticación para mitigar ataques de fuerza bruta.
2. **Motor de Reputación Dinámica:**
   - Cálculo de puntaje acotado entre **0 y 1000 puntos** (`PuntajeReputacion`).
   - Clasificación automática en 4 niveles (`NivelReputacion`): `BAJO`, `NORMAL`, `BUENO` y `EXCELENTE`.
   - Recompensas automáticas por recogida puntual (+10 pts) y devolución puntual (+10 pts).
3. **Gestión de Sanciones con Expiración:**
   - Aplicación de sanciones por `TARDANZA`, `DANO_PARCIAL`, `DANO_TOTAL` e `INASISTENCIA_RESERVA`, con cálculo automático de descuento de puntos y fecha de expiración obligatoria (`fecha_fin`).
   - Una sanción deja de bloquear sola cuando `fecha_fin <= ahora` (no hay tarea programada: la vigencia se evalúa al consultar) y existe el endpoint de amnistía mensual (`POST /reputacion/amnistia`).
4. **Excepciones Académicas:**
   - Registro (`POST /reputacion/excepciones`) y anulación (`POST /reputacion/excepciones/{id}/anular`) de excepciones académicas justificadas por parte de gestión. Mientras la excepción esté vigente, cubre las sanciones de tipo `TARDANZA` e `INASISTENCIA_RESERVA` (nunca los daños).
5. **Interfaz de usuario (`/login`, `/registro`, `/reputacion`):**
   - Pantallas de autenticación y panel de consulta/gestión de reputación, sanciones y excepciones académicas adaptado según el rol del usuario.

---

## 2. Políticas y Reglas de Negocio del Módulo

### Política 1: Escala de Puntaje, Niveles de Reputación y Límites de Operaciones (Spec 006)
- Todo usuario nuevo inicia con **500 puntos** (nivel `NORMAL`).
- El puntaje nunca baja de **0** ni supera **1000** (`sumar_con_tope`).
- Los niveles se determinan automáticamente según el puntaje actual y fijan el cupo máximo de operaciones activas simultáneas (`limite_operaciones`, reservas activas + préstamos en curso):
  - **`EXCELENTE`**: 800 a 1000 puntos → hasta **5** operaciones simultáneas.
  - **`BUENO`**: 600 a 799 puntos → hasta **3** operaciones simultáneas.
  - **`NORMAL`**: 300 a 599 puntos → hasta **2** operaciones simultáneas.
  - **`BAJO`**: 0 a 299 puntos → hasta **1** operación simultánea.

### Política 2: Recompensas por Cumplimiento
- **Entrega / recogida puntual (`premiar_entrega_puntual`):** Suma **+10 puntos** cuando el usuario recoge el recurso en o antes de la fecha de inicio pactada.
- **Devolución puntual (`premiar_devolucion_puntual`):** Suma **+10 puntos** (mismo método de dominio `premiar_puntualidad`, con tope 1000) cuando devuelve el recurso sin días de retraso y sin daños físicos.
- **Amnistía mensual (`POST /reputacion/amnistia`):** Suma **+25 puntos** solo a los perfiles de nivel `BAJO` que no tengan ninguna sanción aplicada en los últimos 30 días. No desbloquea préstamos: solo recupera puntos.

### Política 3: Sanciones y Expiración Temporal
Toda sanción tiene una `fecha_fin` obligatoria (`NOT NULL`). Una sanción está vigente únicamente mientras `fecha_fin > ahora` y `activa == True`. Los valores salen de `TipoSancion` (`puntos_descuento`, `monto_descuento`, `duracion_bloqueo`):

| Tipo | Puntos | Deuda registrada | Duración del bloqueo |
|---|---|---|---|
| `TARDANZA` | −10 | $0 | Gracia de 1 día: con 1 día de retraso solo descuenta puntos (0 días de bloqueo); desde 2 días, **1 día de bloqueo por día de retraso** |
| `DANO_PARCIAL` | −30 | $50 | 30 días |
| `DANO_TOTAL` | −100 | valor del recurso (se calcula en el servicio) | 60 días |
| `INASISTENCIA_RESERVA` | −15 | $0 | 3 días |

- El **retraso se calcula por días calendario en UTC** (`fecha_devolucion.date() - fecha_fin.date()`).
- Desde la devolución en ventanilla (`prestamos`) solo se aplican hoy `TARDANZA` y `DANO_PARCIAL`. `DANO_TOTAL` e `INASISTENCIA_RESERVA` se aplican manualmente por gestión (`POST /reputacion/sanciones`).

### Política 4: Bloqueo Operativo y Excepciones Académicas
- El **nivel de reputación no bloquea** por sí solo: únicamente fija la prioridad en la lista de espera y el cupo de operaciones simultáneas.
- Un usuario es elegible para operar si no cuenta con ninguna sanción vigente (`activa` y `fecha_fin > ahora`) que no esté cubierta por una excepción.
- Si posee una sanción vigente de tipo `TARDANZA` o `INASISTENCIA_RESERVA`, puede operar si tiene una **Excepción Académica** vigente (`fecha_inicio <= ahora <= fecha_fin`, no anulada). Las sanciones por daños (`DANO_PARCIAL`, `DANO_TOTAL`) nunca se cubren con excepción.

### Política 5: Administración de Usuarios, Jerarquía de Roles y Estado de Cuenta (Spec 006)
- **Creación de usuarios (`POST /usuarios`):**
  - Si el actor en sesión es `GESTOR_ALMACEN` (sin rol de administrador), solo puede asignar roles solicitantes (`ESTUDIANTE`, `DOCENTE`, `PERSONAL_ADMINISTRATIVO`); si intenta asignar roles de gestión, el servidor rechaza con `403 Forbidden`.
  - Si el actor en sesión es `ADMINISTRADOR_SISTEMA`, puede asignar cualquiera de los 5 roles del sistema.
  - Si no se especifica rol en la petición, se asigna `ESTUDIANTE` por defecto.
- **Cambio de rol (`PATCH /usuarios/{id}/rol`):**
  - Acción exclusiva para `ADMINISTRADOR_SISTEMA` (`403` para otros roles).
  - Autoprotección: el administrador no puede quitarse a sí mismo el rol `ADMINISTRADOR_SISTEMA` (`409 Conflict`).
- **Activación y desactivación de cuentas (`PATCH /usuarios/{id}/estado`):**
  - Acción exclusiva para `ADMINISTRADOR_SISTEMA`.
  - Autoprotección: el administrador no puede desactivar su propia cuenta (`409 Conflict`).
  - Bloqueo inmediato: las cuentas inactivas (`estado = False`) son rechazadas con `403 Forbidden` (`"La cuenta de usuario está desactivada"`) tanto al iniciar sesión en `/auth/login` como al presentar un token emitido previamente en `get_current_user`.
- **Eliminación de usuarios (`DELETE /usuarios/{id}`):**
  - Acción exclusiva para `ADMINISTRADOR_SISTEMA` con confirmación inline en dos pasos en frontend.
  - Autoprotección: el administrador no puede eliminar su propia cuenta (`409 Conflict`).
  - Protección de operaciones activas: se consulta a `ReservaService` y `PrestamoService`; si el usuario tiene reservas activas (`PENDIENTE` o `CONFIRMADA`) o préstamos en curso (`ACTIVO`, `ENTREGADO` o `VENCIDO`), se rechaza con `409 Conflict`.
  - Si procede, se eliminan en cascada sus excepciones académicas, perfil de reputación y sanciones asociadas.

---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/identidad_reputacion/domain/`)
- **`enums/nivel_reputacion.py` (`NivelReputacion`)**:
  - Define los cuatro niveles (`BAJO`, `NORMAL`, `BUENO`, `EXCELENTE`) y la propiedad `limite_operaciones -> int` (1, 2, 3, 5) que determina el tope de operaciones activas simultáneas del usuario (Spec 006).
- **`entities/usuario.py` (`Usuario`)**:
  - `cambiar_roles(nuevos_roles)`: Valida lista no vacía y reemplaza los roles.
  - `establecer_estado(activo)`: Actualiza el estado activo/inactivo de la cuenta.
- **`entities/perfil_reputacion.py` (`PerfilReputacion`)**:
  - `crear_para_usuario(usuario_id)`: Fábrica del perfil inicial (500 puntos, nivel `NORMAL`).
  - `recalcular_nivel()`: `BAJO` (0–299), `NORMAL` (300–599), `BUENO` (600–799), `EXCELENTE` (800–1000).
  - `aplicar_sancion(sancion)`: Registra la sanción, resta los puntos y recalcula el `NivelReputacion`.
  - `premiar_puntualidad()`: Suma 10 puntos con tope 1000 y recalcula el nivel.
  - `sancion_bloqueante(excepciones_vigentes)` y `es_elegible_para_prestamo(...)`: Deciden si alguna sanción vigente (no cubierta por excepción) bloquea al usuario.
  - `aplicar_amnistia()`: Suma 25 puntos solo si el nivel es `BAJO` y no hubo sanciones aplicadas en los últimos 30 días.
- **`entities/sancion.py` (`Sancion`)**:
  - `aplicar()` la marca activa y `esta_vigente(ahora)` evalúa `activa` y `fecha_fin > ahora`. La duración y los puntos se derivan de `TipoSancion` (`puntos_descuento`, `monto_descuento`, `duracion_bloqueo`).
- **`value_objects/puntaje_reputacion.py` (`PuntajeReputacion`)**:
  - Value Object inmutable que valida el rango `0 <= puntos <= 1000` (`sumar_con_tope` y `restar`).
- **`entities/excepcion_academica.py` (`ExcepcionAcademica`)**:
  - `anular()` y `es_vigente(ahora)`.

### Capa de Aplicación (`contexts/identidad_reputacion/application/`)
- **`reputacion_service.py` (`ReputacionService`)**:
  - `obtener_perfil(usuario_id)`: Devuelve el `PerfilReputacionDTO` (si no existe, lo crea con 500 puntos). Es usado también por el contexto `reservas` para ordenar la lista de espera.
  - `consultar_elegibilidad_lectura(usuario_id)`, `consultar_nivel_lectura(usuario_id)`, `consultar_puntaje_lectura(usuario_id)`: Consultas puras de lectura sin efectos secundarios para inspección y validación.
  - `aplicar_sancion(...)`, `premiar_entrega_puntual(...)`, `premiar_devolucion_puntual(...)`: Llamados desde el contexto `prestamos` al entregar o devolver un recurso.
  - `obtener_elegibilidad(usuario_id)`: Evalúa bloqueo por sanciones vigentes y excepciones académicas activas.
- **`usuario_service.py` (`UsuarioService`)**:
  - `crear_usuario(datos, actor)`: Alta de cuentas con control jerárquico de roles según permisos del actor.
  - `cambiar_rol_usuario(id_usuario, nuevo_rol, actor)`: Cambio de rol exclusivo para administrador con autoprotección 409.
  - `cambiar_estado_usuario(id_usuario, estado, actor)`: Activación/desactivación con autoprotección 409.
  - `eliminar_usuario(id_usuario, actor)`: Eliminación segura verificando ausencia de reservas activas (`contar_reservas_activas_usuario`) y préstamos en curso (`contar_prestamos_en_curso`).
- **`autenticacion_service.py` (`AutenticacionService`)**:
  - `registrar_usuario(...)`, `login(...)` (con bloqueo 403 para cuentas inactivas), `validar_token(...)`.

### Capa de Presentación y Frontend
- **`presentation/dependencies.py`**:
  - `get_current_user`: Extrae y valida el JWT de la petición, verificando que la cuenta esté activa (`403` si `estado = False`).
  - `require_roles(*roles)`: Dependencia de FastAPI usada en todos los contextos para proteger endpoints exclusivos de `GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA`.
- **`presentation/usuario_controller.py`**: Endpoints bajo `/usuarios` (`POST`, `GET`, `PATCH /{id}/rol`, `PATCH /{id}/estado`, `DELETE /{id}`).
- **`presentation/reputacion_controller.py` y `autenticacion_controller.py`**: Endpoints REST bajo `/reputacion` y `/auth`.
- **`frontend/src/features/identidad/pages/UsuariosPage.jsx`**: Pantalla de administración de usuarios con selector jerárquico de roles en el alta, cambio de rol inline, conmutador de estado activo/inactivo y eliminación con confirmación en dos pasos.
- **`frontend/src/features/identidad/pages/GestionReputacionPage.jsx`**: Vista de gestión donde el gestor o administrador aplica sanciones, aprueba/anula excepciones académicas o ejecuta amnistías.

