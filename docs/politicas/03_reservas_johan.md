# Contexto 3: Gestión de Reservas (`reservas`)

**Responsable:** Integrante 3 (Johan)  
**Backend:** `backend/src/prestamos_recursos/contexts/reservas/`  
**Frontend:** `frontend/src/features/reservas/`  
**Schema BD:** `reservas`

---

## 1. Qué se implementó en este contexto

1. **Solicitud de Reservas con Autoconfirmación o Encolamiento (`crear_reserva`):**
   - Validación de rango horario (`fecha_fin > fecha_inicio`) y normalización a UTC.
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

### Política 1: Validación de Horarios y Prohibición de Duplicados del Mismo Usuario
- Toda reserva exige `fecha_fin > fecha_inicio` (de lo contrario lanza `ValueError("fecha_fin debe ser posterior a fecha_inicio")`).
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
- Solo `GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA` pueden confirmar manualmente reservas pendientes o iniciar el préstamo (`POST /reservas/{id}/prestamo`).

---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/reservas/domain/`)
- **`entities/reserva.py` (`Reserva`)**:
  - `Reserva.crear(...)`: Método de fábrica que valida `fecha_fin > fecha_inicio` e inicializa el estado en `PENDIENTE`.
  - `confirmar()`: Verifica que esté `PENDIENTE` y vigente (`esta_vigente()`), y cambia el estado a `CONFIRMADA`.
  - `cancelar()`: Impide cancelar una reserva ya cancelada y pasa el estado a `CANCELADA`.
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
