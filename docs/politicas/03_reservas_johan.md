# Contexto 3: Gestión de Reservas (`reservas`)

**Responsable:** Integrante 3 (Johan)  
**Backend:** `backend/src/prestamos_recursos/contexts/reservas/`  
**Frontend:** `frontend/src/features/reservas/`  
**Schema BD:** `reservas`

---

## 1. Qué se implementó en este contexto

1. **Solicitud de Reservas con Autoconfirmación o Encolamiento (`crear_reserva`):**
   - Validación de políticas temporales e institucionales (Spec 007): horario de atención de **lunes a viernes de 08:00 a 20:00 UTC** inclusive tanto para inicio como para fin, duración mínima de **1 hora** y máxima de **7 días**, prohibición de fechas en el pasado (con tolerancia de 5 minutos) y anticipación máxima de **30 días**.
   - Verificación del estado operativo del recurso vía `RecursoApplicationService`: se admiten recursos en `DISPONIBLE` y `EN_USO`; se rechazan recursos en `MANTENIMIENTO` o `FUERA_DE_SERVICIO` con `409 Conflict`.
   - Si el horario solicitado para ese recurso no choca con ninguna reserva `CONFIRMADA`, la reserva se confirma automáticamente en el acto (`CONFIRMADA`).
   - Si otro usuario ya tiene una reserva `CONFIRMADA` que se cruza en ese horario, la solicitud no se pierde: se registra en la **Lista de Espera** en estado `PENDIENTE`.

2. **Algoritmo de Prioridad por Reputación (`AlgoritmoPrioridadService`):**
   - Servicio de dominio puro que ordena la cola de espera de un recurso priorizando a los usuarios con **mayor puntaje de reputación** (obtenido del contexto `identidad_reputacion`) y desempatando por orden de llegada (`fecha_inicio` más antigua).
3. **Promoción Automática al Cancelar (`cancelar_reserva`):**
   - Cuando se cancela una reserva que estaba `CONFIRMADA`, el sistema busca todas las reservas `PENDIENTE` vigentes que esperaban ese horario, las ordena con `AlgoritmoPrioridadService` según la reputación de sus titulares y **confirma automáticamente** a la candidata más prioritaria que no tenga cruces con otras confirmadas.
4. **Conversión de Reserva a Préstamo y Permisos por Rol:**
   - Restricción de confirmación manual (`PATCH /reservas/{id}/confirmar`) e inicio de préstamo (`POST /reservas/{id}/prestamo`) exclusivamente a los roles de gestión (`GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA`).
   - Listado propio para estudiantes/docentes y listado global (`GET /reservas`) para personal de gestión.

---

## 2. Políticas y Reglas de Negocio del Módulo

### Política 1: Reglas Temporales y Horario de Atención Institucional (Spec 007)
- **Horario de atención institucional:** Las fechas y horas de entrega (`fecha_inicio`) y devolución (`fecha_fin`) deben ubicarse estrictamente de **lunes a viernes entre las 08:00 y las 20:00 UTC** inclusive (`Reserva._validar_horario_atencion`). Se rechaza cualquier solicitud en fin de semana (sábado/domingo) o fuera del horario de ventanilla con `409 Conflict`. Se permiten reservas multidía (p. ej. de viernes 15:00 a lunes 15:00) siempre que ambos extremos caigan dentro del horario hábil.
- **Duración de la reserva:**
  - Duración mínima de **1 hora** (`duracion >= timedelta(hours=1)`).
  - Duración máxima de **7 días** (`duracion <= timedelta(days=7)`).
  - Toda reserva exige `fecha_fin > fecha_inicio`.
- **Ventana temporal de anticipación y no pasado:**
  - Prohibido reservar en el pasado respecto al instante actual, permitiendo una tolerancia de **5 minutos** para compensar desfases de reloj entre cliente y servidor.
  - Anticipación máxima permitida: **30 días** respecto a `fecha_inicio`.
- **Superposición y unicidad:** Dos reservas se superponen cuando `inicio_A < fin_B` y `inicio_B < fin_A` (`se_superpone_con`). Un mismo usuario no puede tener dos reservas activas superpuestas para el mismo recurso (`409 Conflict`).

### Política 2: Autoconfirmación vs. Lista de Espera (`PENDIENTE`)
- **Horario libre:** Si ninguna reserva `CONFIRMADA` se superpone con el horario pedido, la reserva pasa a `EstadoReserva.CONFIRMADA` inmediatamente al crearse (`201 Created`).
- **Horario ocupado por otro usuario:** Si ya existe una reserva `CONFIRMADA` en ese rango, la nueva reserva se guarda en estado `EstadoReserva.PENDIENTE` (en lista de espera) e informa al usuario en pantalla que su solicitud será priorizada según su reputación.

### Política 3: Priorización en Cola de Espera por Reputación
El servicio `AlgoritmoPrioridadService.ordenar_cola_espera(reservas, puntajes_reputacion)`:
1. Filtra únicamente reservas en estado `PENDIENTE` que sigan vigentes (`fecha_fin > ahora`).
2. Ordena aplicando la clave `(-puntaje, fecha_inicio_utc)`:
   - **Criterio 1 (Reputación):** Va primero quien tenga mayor puntaje en `identidad_reputacion` (por ejemplo, un usuario con 850 pts supera a uno con 500 pts aunque haya reservado después). Si un usuario no tiene puntaje registrado, se asume el valor base de `500`.
   - **Criterio 2 (Antigüedad / FIFO):** A igual puntaje de reputación, tiene prioridad quien solicitó el horario más temprano.

### Política 4: Promoción Automática en Cancelación y Reglas de Acceso
- Tanto el titular de la reserva como el personal de gestión pueden cancelar una reserva (`PENDIENTE` o `CONFIRMADA`).
- Si la reserva cancelada estaba `CONFIRMADA`, el sistema ejecuta automáticamente la promoción de la cola de espera para que el horario liberado pase al primer candidato elegible por reputación sin necesidad de intervención manual.
- **Filtro de elegibilidad en promoción (Spec 006):** Durante la promoción automática, el sistema consulta `_es_usuario_elegible(candidata.usuario_id)` y **salta automáticamente** a cualquier candidato que tenga una sanción bloqueante activa no cubierta por excepción académica, promoviendo al siguiente en la lista.
- Solo `GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA` pueden confirmar manualmente reservas pendientes o iniciar el préstamo (`POST /reservas/{id}/prestamo`).

### Política 5: Segregación de Funciones, Elegibilidad por Sanciones y Cupo Simultáneo por Reputación (Spec 006)
1. **Segregación de funciones en reservas:**
   - Quienes administran y entregan bienes no pueden auto-solicitarse préstamos: si un usuario autenticado con rol `GESTOR_ALMACEN` o `ADMINISTRADOR_SISTEMA` envía `POST /reservas`, el servidor responde `403 Forbidden` (*"las cuentas de gestión y administración no pueden solicitar reservas ni préstamos para sí mismas"*).
   - En la interfaz `/reservas`, los roles de gestión ven el encabezado «Gestión de reservas» y no visualizan el formulario de solicitud.
2. **Bloqueo por sanción vigente:**
   - Al invocar `crear_reserva`, `confirmar_reserva` o `convertir_a_prestamo`, el sistema verifica `_verificar_elegibilidad_usuario(usuario_id)` consultando a `ReputacionService`. Si el titular tiene una sanción vigente activa no amparada por una excepción académica, la operación se rechaza con `409 Conflict`.
3. **Límite de operaciones simultáneas por nivel de reputación:**
   - En `crear_reserva`, `_verificar_limite_operaciones_simultaneas` consulta el nivel del usuario en `ReputacionService` (`NivelReputacion.limite_operaciones`) y contabiliza:
     `total_en_curso = contar_reservas_activas_usuario(usuario_id) + prestamo_service.contar_prestamos_en_curso(usuario_id)`
   - Si `total_en_curso >= nivel.limite_operaciones` (`BAJO`: 1, `NORMAL`: 2, `BUENO`: 3, `EXCELENTE`: 5), la solicitud se rechaza con `409 Conflict` informando el límite del nivel.


### Política 6: Ventana de Conversión a Préstamo y Estado Operativo del Recurso (Spec 007)
1. **Estado operativo del recurso:**
   - Al procesar `crear_reserva`, `ReservaService` valida el estado del recurso mediante `RecursoApplicationService`.
   - Se admiten recursos en estado `DISPONIBLE` y `EN_USO` (para fechas futuras o lista de espera).
   - Se rechazan reservas para recursos en `MANTENIMIENTO` o `FUERA_DE_SERVICIO` con `409 Conflict` (`"el recurso no admite reservas por encontrarse en mantenimiento o fuera de servicio"`).
2. **Ventana temporal de conversión a préstamo:**
   - La conversión a préstamo en ventanilla (`convertir_a_prestamo`) exige que el instante actual se encuentre dentro del intervalo:
     `fecha_inicio - 1 hora <= ahora <= fecha_fin`
   - Si se intenta iniciar el préstamo antes de 1 hora del inicio pactado o después de que la reserva haya vencido, se rechaza con `409 Conflict`.

---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/reservas/domain/`)
- **`entities/reserva.py` (`Reserva`)**:
  - `Reserva.crear(...)`: Valida horario hábil institucional (Lunes a Viernes 08:00 a 20:00 UTC), duración mínima (1h) y máxima (7d), e inicializa el estado en `PENDIENTE`. `__post_init__` valida que `fecha_fin > fecha_inicio`.
  - `confirmar(fecha_actual)`: Verifica que esté `PENDIENTE` y vigente en el instante evaluado (`esta_vigente(fecha_actual)`), y cambia el estado a `CONFIRMADA`.
  - `cancelar()`: Impide cancelar una reserva `CANCELADA`, `VENCIDA` o `CONVERTIDA` y pasa el estado a `CANCELADA`.
  - `esta_vigente(fecha_actual)`: Comprueba si `fecha_fin >= ahora` y el estado está activo (`PENDIENTE` o `CONFIRMADA`).
  - `se_superpone_con(otra: Reserva) -> bool`: Compara en UTC si dos intervalos `[fecha_inicio, fecha_fin)` se solapan.
- **`services/algoritmo_prioridad_service.py` (`AlgoritmoPrioridadService`)**:
  - `ordenar_cola_espera(reservas, puntajes_reputacion=None)`: Ordena por `(-puntajes.get(r.usuario_id, 500), r.fecha_inicio)`.

### Capa de Aplicación (`contexts/reservas/application/`)
- **`reserva_service.py` (`ReservaService`)**:
  - Desacople DDD mediante `RecursoApplicationService` inyectado como `catalogo_service`.
  - `crear_reserva(datos, ahora=None)`: Valida estado del recurso, ventana de creación (no pasado con 5 min de tolerancia, máx. 30 días de anticipación), superposición con el mismo usuario y confirma o encola en `PENDIENTE`.
  - `cancelar_reserva(id_reserva)`: Cancela la reserva y promueve automáticamente al mejor candidato elegible saltando sancionados.
  - `convertir_a_prestamo(id_reserva, ahora=None)`: Valida ventana operativa `inicio - 1h <= ahora <= fin` y delega en `PrestamoService`.

### Capa de Presentación y Frontend
- **`presentation/reserva_controller.py`**:
  - Endpoints `/reservas`, `/reservas/usuario/{id_usuario}`, `/reservas/recurso/{id_recurso}/cola`, `PATCH /reservas/{id}/confirmar`, `POST /reservas/{id}/prestamo` y `PATCH /reservas/{id}/cancelar`.
- **`frontend/src/features/reservas/pages/MisReservasPage.jsx`**:
  - Formulario de solicitud (que lee `?recursoId=` si el usuario vino desde el catálogo), alerta informativa cuando una reserva queda en cola de espera por reputación, y tabla de acciones diferenciada por rol (`esGestion`).
  - Función `formatearFechaNominalUTC` para neutralizar desfases de zona horaria del navegador.
  - Opciones de recursos no operativos (`MANTENIMIENTO` / `FUERA_DE_SERVICIO`) deshabilitadas en el selector (`— (No disponible para reservas)`).
  - Validaciones locales antes de envío (duración 1h a 7d, L–V 08:00 a 20:00) y texto informativo de políticas operativas.

---

## 4. Limitaciones conocidas

- **`VENCIDA` sin asignación automática:** el estado existe en `EstadoReserva` y bloquea la cancelación, pero ninguna tarea lo asigna cuando el usuario no se presenta: una reserva `CONFIRMADA` solo cambia por confirmación, cancelación o conversión a préstamo. La sanción `INASISTENCIA_RESERVA` también se registra manualmente.
- **Sin bloqueo exclusivo de stock por reserva futura:** al crear una reserva se verifica que el recurso no esté en `MANTENIMIENTO` ni `FUERA_DE_SERVICIO`, pero no se cambia el estado del recurso a «reservado» (el catálogo solo tiene `DISPONIBLE`, `EN_USO`, `MANTENIMIENTO` y `FUERA_DE_SERVICIO`).
- **Dependencias de código:** `ReservaService` importa `PrestamoService` y `NivelReputacion`; las referencias de datos siguen siendo solo por ID.
