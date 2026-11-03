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
   - Clasificación automática en 4 niveles (`NivelReputacion`): `EXCELENTE`, `NORMAL`, `RIESGO` y `BLOQUEADO`.
   - Recompensas automáticas por recogida puntual (+10 pts) y devolución puntual (+15 pts).
3. **Gestión de Sanciones con Expiración:**
   - Aplicación de sanciones por `TARDANZA`, `DANO_PARCIAL` y `PERDIDA_TOTAL`, con cálculo automático de descuento de puntos y fecha de expiración obligatoria (`fecha_fin`).
   - Expiración automática de sanciones vencidas y endpoint de amnistía administrativa.
4. **Excepciones Académicas:**
   - Solicitud, aprobación y rechazo de excepciones académicas justificadas para permitir que un usuario en estado `BLOQUEADO` pueda operar temporalmente cuando un gestor o administrador lo autoriza.
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
- **Devolución puntual (`premiar_devolucion_puntual`):** Suma **+15 puntos** cuando devuelve el recurso sin días de retraso y sin daños físicos.

### Política 3: Sanciones y Expiración Temporal
Toda sanción tiene una `fecha_fin` obligatoria (`NOT NULL`). Una sanción está vigente únicamente mientras `fecha_fin > ahora` y `activa == True`:
- **`DEVOLUCION_TARDIA`:** Descuenta **20 puntos base + 5 puntos por cada día de retraso** (`20 + 5 * dias_retardo`). Duración: 15 días.
- **`DANO_LEVE`:** Descuenta **50 puntos**. Duración: 7 días.
- **`DANO_GRAVE`:** Descuenta **150 puntos**. Duración: 30 días.
- **`DANO_TOTAL`:** Descuenta **300 puntos**. Duración: 180 días.
- **`INASISTENCIA_RESERVA`:** Descuenta **30 puntos**. Duración: 7 días.

### Política 4: Bloqueo Operativo y Excepciones Académicas
- Un usuario es elegible para operar si no cuenta con sanciones vigentes activas que bloqueen el acceso.
- Si posee una sanción vigente, solo puede operar si cuenta con una **Excepción Académica** activa que justifique su sanción cuya vigencia cubra la fecha actual (`fecha_inicio <= ahora <= fecha_fin`).

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
  - `aplicar_sancion(sancion)`: Registra la sanción, resta los puntos y recalcula el `NivelReputacion`.
  - `recompensar(puntos)`: Incrementa el puntaje hasta el tope de 1000 y actualiza el nivel.
  - `expirar_sanciones_vencidas(ahora)`: Desactiva las sanciones cuya `fecha_fin <= ahora`.
  - `aplicar_amnistia()`: Desactiva todas las sanciones activas y restaura el puntaje a 500 si estaba por debajo.
- **`entities/sancion.py` (`Sancion`)**:
  - `calcular_descuento(tipo, dias_retardo)` y `calcular_fecha_fin(tipo, fecha_aplicacion)`: Contienen las fórmulas exactas de castigo y duración.
- **`value_objects/puntaje_reputacion.py` (`PuntajeReputacion`)**:
  - Value Object inmutable que valida el rango `0 <= valor <= 1000`.
- **`entities/excepcion_academica.py` (`ExcepcionAcademica`)**:
  - `aprobar()`, `rechazar()` y `esta_vigente(ahora)`.

### Capa de Aplicación (`contexts/identidad_reputacion/application/`)
- **`reputacion_service.py` (`ReputacionService`)**:
  - `obtener_perfil(usuario_id)`: Expira sanciones vencidas y devuelve el `PerfilReputacionDTO`. Es usado también por el contexto `reservas` para ordenar la lista de espera.
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

