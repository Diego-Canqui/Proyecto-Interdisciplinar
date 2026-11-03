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

### Política 1: Escala de Puntaje y Niveles de Reputación
- Todo usuario nuevo inicia con **500 puntos** (nivel `NORMAL`).
- El puntaje nunca baja de **0** ni supera **1000** (`sumar_con_tope`).
- Los niveles se determinan automáticamente según el puntaje actual:
  - **`EXCELENTE`**: 800 a 1000 puntos.
  - **`NORMAL`**: 500 a 799 puntos.
  - **`RIESGO`**: 200 a 499 puntos.
  - **`BLOQUEADO`**: 0 a 199 puntos (o cuando tiene una sanción vigente de pérdida total).

### Política 2: Recompensas por Cumplimiento
- **Entrega / recogida puntual (`premiar_entrega_puntual`):** Suma **+10 puntos** cuando el usuario recoge el recurso en o antes de la fecha de inicio pactada.
- **Devolución puntual (`premiar_devolucion_puntual`):** Suma **+15 puntos** cuando devuelve el recurso sin días de retraso y sin daños físicos.

### Política 3: Sanciones y Expiración Temporal
Toda sanción tiene una `fecha_fin` obligatoria (`NOT NULL`). Una sanción está vigente únicamente mientras `fecha_fin > ahora` y `activa == True`:
- **`TARDANZA`:** Descuenta **20 puntos base + 5 puntos por cada día de retraso** (`20 + 5 * dias_retardo`). Duración: 15 días.
- **`DANO_PARCIAL`:** Descuenta **100 puntos**. Duración: 30 días.
- **`PERDIDA_TOTAL`:** Descuenta el total de puntos llevando el puntaje a **0** (`BLOQUEADO`). Duración: 180 días.

### Política 4: Bloqueo Operativo y Excepciones Académicas
- Un usuario está habilitado para operar (`puede_operar`) si su nivel no es `BLOQUEADO` (puntaje >= 200 y sin sanción de pérdida total activa).
- Si está bloqueado, solo puede operar si cuenta con una **Excepción Académica** en estado `APROBADA` cuya `fecha_limite >= ahora`.

---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/identidad_reputacion/domain/`)
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
  - `aplicar_sancion(...)`, `premiar_entrega_puntual(...)`, `premiar_devolucion_puntual(...)`: Llamados desde el contexto `prestamos` al entregar o devolver un recurso.
  - `puede_operar(usuario_id)`: Evalúa bloqueo y excepciones académicas vigentes.
- **`autenticacion_service.py` (`AutenticacionService`)**:
  - `registrar_usuario(...)`, `autenticar_usuario(...)`, `verificar_token(...)`.

### Capa de Presentación y Frontend
- **`presentation/dependencies.py`**:
  - `get_current_user`: Extrae y valida el JWT de la petición.
  - `require_roles(*roles)`: Dependencia de FastAPI usada en todos los contextos para proteger endpoints exclusivos de `GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA`.
- **`presentation/reputacion_controller.py` y `autenticacion_controller.py`**: Endpoints REST bajo `/reputacion` y `/auth`.
- **`frontend/src/features/identidad/pages/GestionReputacionPage.jsx`**: Vista donde el estudiante consulta su puntaje/sanciones/excepciones y el administrador aplica sanciones, aprueba excepciones o ejecuta amnistías.
