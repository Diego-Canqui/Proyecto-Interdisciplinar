# Contexto 3: Gestión de Reservas (`reservas`)

**Responsable:** Integrante 3 (Johan)  
**Backend:** `backend/src/prestamos_recursos/contexts/reservas/`  
**Frontend:** `frontend/src/features/reservas/`  
**Schema BD:** `reservas`

---

## 1. Qué se implementó en este contexto

1. **Solicitud de Reservas con Autoconfirmación o Encolamiento (`crear_reserva`):**
   - Validación de rango horario (`fecha_fin > fecha_inicio`), normalización a UTC y verificación de duración máxima de **7 días** (`DURACION_MAXIMA_RESERVA = timedelta(days=7)`, Spec 006).
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

### Política 1: Validación de Horarios, Duración Máxima y Prohibición de Duplicados
- Toda reserva exige `fecha_fin > fecha_inicio` (de lo contrario lanza `ValueError("fecha_fin debe ser posterior a fecha_inicio")`).
- **Duración máxima de 7 días (Spec 006):** En `Reserva.crear()` se valida que `fecha_fin - fecha_inicio <= timedelta(days=7)` (168 horas). Si la duración solicitada supera los 7 días, se rechaza con `409 Conflict` (`ValueError("la duración máxima de una reserva es de 7 días")`).
- Dos reservas se superponen cuando `inicio_A < fin_B` y `inicio_B < fin_A` (`se_superpone_con`). Los horarios consecutivos exactos (donde una termina a las 12:00 y otra empieza a las 12:00) son válidos y no chocan.
- Un mismo usuario **no puede** crear dos reservas activas que se superpongan para el mismo recurso (responde `409 Conflict`: *"ya tienes una reserva activa para este recurso en ese horario"*).

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


---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/reservas/domain/`)
- **`entities/reserva.py` (`Reserva`)**:
  - `Reserva.crear(...)`: Método de fábrica que valida la duración máxima de 7 días e inicializa el estado en `PENDIENTE`. `__post_init__` valida que `fecha_fin > fecha_inicio`.
  - `confirmar()`: Verifica que esté `PENDIENTE` y vigente (`esta_vigente()`), y cambia el estado a `CONFIRMADA`.
  - `cancelar()`: Impide cancelar una reserva `CANCELADA`, `VENCIDA` o `CONVERTIDA` y pasa el estado a `CANCELADA`.
  - `se_superpone_con(otra: Reserva) -> bool`: Compara en UTC si dos intervalos `[fecha_inicio, fecha_fin)` se solapan.
- **`services/algoritmo_prioridad_service.py` (`AlgoritmoPrioridadService`)**:
  - `ordenar_cola_espera(reservas, puntajes_reputacion=None)`: Ordena por `(-puntajes.get(r.usuario_id, 500), r.fecha_inicio)`.

### Capa de Aplicación (`contexts/reservas/application/`)
- **`reserva_service.py` (`ReservaService`)**:
  - `crear_reserva(datos)`: Evalúa superposición con reservas del mismo usuario (error) y con reservas confirmadas de otros usuarios (cola `PENDIENTE` o autoconfirmación).
  - `cancelar_reserva(id_reserva)`: Cancela la reserva y, si estaba `CONFIRMADA`, consulta los puntajes en `ReputacionService`, ordena la cola con `AlgoritmoPrioridadService` y confirma la candidata ganadora.
  - `obtener_cola_espera(id_recurso)`: Devuelve la cola de espera ya ordenada por reputación.
  - `convertir_a_prestamo(id_reserva)`: Verifica que la reserva esté `CONFIRMADA` y delega en `PrestamoService.crear_desde_reserva(...)`.

### Capa de Presentación y Frontend
- **`presentation/reserva_controller.py`**:
  - Endpoints `/reservas`, `/reservas/usuario/{id_usuario}`, `/reservas/recurso/{id_recurso}/cola`, `PATCH /reservas/{id}/confirmar`, `POST /reservas/{id}/prestamo` y `PATCH /reservas/{id}/cancelar`.
- **`frontend/src/features/reservas/pages/MisReservasPage.jsx`**:
  - Formulario de solicitud (que lee `?recursoId=` si el usuario vino desde el catálogo), alerta informativa cuando una reserva queda en cola de espera por reputación, y tabla de acciones diferenciada por rol (`esGestion`).

---

## 4. Limitaciones conocidas

- **`VENCIDA` sin asignación automática:** el estado existe en `EstadoReserva` y bloquea la cancelación, pero ninguna tarea lo asigna cuando el usuario no se presenta: una reserva `CONFIRMADA` solo cambia por confirmación, cancelación o conversión a préstamo. La sanción `INASISTENCIA_RESERVA` también se registra manualmente.
- **Sin consulta previa al catálogo:** `crear_reserva` no verifica que el `recurso_id` exista ni que esté `DISPONIBLE`; esa validación se hace al iniciar el préstamo (`PrestamoService.solicitar_prestamo`). Tampoco cambia el estado del recurso a «reservado» (el catálogo solo tiene `DISPONIBLE`, `EN_USO`, `MANTENIMIENTO` y `FUERA_DE_SERVICIO`).
- **Dependencias de código:** `ReservaService` importa `PrestamoService` y `NivelReputacion`; las referencias de datos siguen siendo solo por ID.
