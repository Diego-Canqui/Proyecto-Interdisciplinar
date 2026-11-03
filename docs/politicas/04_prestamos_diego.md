# Contexto 4: Gestión de Préstamos, Garantías y Checklists (`prestamos`)

**Responsable:** Integrante 4 (Diego Villanueva)  
**Backend:** `backend/src/prestamos_recursos/contexts/prestamos/`  
**Frontend:** `frontend/src/features/prestamos/`  
**Schema BD:** `prestamos`

---

## 1. Qué se implementó en este contexto

1. **Creación de Préstamo desde Reserva Confirmada (`solicitar_prestamo`):**
   - Verificación en el catálogo de que el recurso exista y su estado sea `DISPONIBLE`.
   - Creación del agregado `Prestamo` en estado `ACTIVO` y actualización automática del recurso en el catálogo a `EN_USO`.
2. **Flujo de Entrega Física en Ventanilla (`Garantia` + `Checklist` de salida):**
   - Registro de la garantía institucional (`CARNET_UNIVERSITARIO`, `DOCUMENTO_IDENTIDAD`, `DEPOSITO_ECONOMICO`, `OTRO`) junto con el Value Object `CompromisoResponsabilidad` (contenido del acuerdo, firma, fecha y nombre del testigo/operador).
   - Registro y confirmación del `Checklist` técnico de salida (`ESTADO_INICIAL`: carcasa, pantalla, cables/cargador, coincidencia de nº de serie, observaciones y evidencia fotográfica).
   - Transición del préstamo a `ENTREGADO` y premio automático en la reputación del usuario si recogió puntualmente.
3. **Flujo de Devolución con Inspección de Retorno y Detección de Daños (`procesar_devolucion`):**
   - Cálculo automático de días de retraso respecto a `fecha_fin`.
   - Registro del `Checklist` de retorno (`ESTADO_DEVOLUCION`) indicando observaciones, fotos y si se detectaron daños físicos (`danos_detectados`).
   - Integración directa con `catalogo` e `identidad_reputacion`: libera el recurso a `DISPONIBLE` (o lo envía a `MANTENIMIENTO` si hubo daños) y premia o sanciona al usuario según puntualidad y estado físico.
4. **Consulta de Inspecciones y Renovación (`consultar_inspecciones`, `renovar_prestamo`):**
   - Endpoint y modal en la UI para que tanto el estudiante como el gestor puedan consultar la garantía y los checklists inicial y de retorno de cualquier préstamo.
   - Extensión de plazo (+7 días) para préstamos vigentes antes de su vencimiento.

---

## 2. Políticas y Reglas de Negocio del Módulo

### Política 1: Ciclo de Estados del Préstamo (`EstadoPrestamo`)
Un préstamo pasa por los siguientes estados:
- **`ACTIVO`**: Creado a partir de una reserva confirmada; el recurso ya está reservado como `EN_USO` esperando la formalización en ventanilla.
- **`ENTREGADO`**: El usuario ya dejó su garantía y el gestor confirmó el checklist de salida; el bien está físicamente en custodia del usuario.
- **`DEVUELTO`**: El bien fue recibido de vuelta en almacén y pasó la inspección de retorno.
- **`VENCIDO`**: Superó su `fecha_fin` sin haber sido devuelto.
- **`CANCELADO`**: Cancelado administrativamente antes de ser devuelto.

### Política 2: Requisitos de Entrega Física (Garantía + Checklist Inicial)
- Solo un préstamo en estado `ACTIVO` puede iniciar y completar el proceso de entrega.
- Para marcar un préstamo como `ENTREGADO` es obligatorio:
  1. Que exista un `Checklist` de tipo `ESTADO_INICIAL` confirmado (`checklist.completo == True`).
  2. Que exista una `Garantia` asociada en estado `REGISTRADA` con un `CompromisoResponsabilidad` válido (`contenido`, `firma_url` y `testigo` no vacíos).
- **Premio por recogida puntual:** Si la fecha de entrega es menor o igual a la fecha de inicio pactada (`hoy <= fecha_inicio`), se invoca `reputacion_service.premiar_entrega_puntual(usuario_id)` (+10 pts).

### Política 3: Recepción Física, Retrasos y Daños en la Devolución
- Solo el personal de gestión (`GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA`) puede registrar la devolución (`POST /prestamos/{id}/devolucion`).
- Un préstamo ya `DEVUELTO` o `CANCELADO` no puede volver a devolverse (responde `409 Conflict`).
- Al procesar la devolución:
  1. **Cálculo de retraso (`calcular_dias_retraso`):** `max(0, (fecha_devolucion.date() - fecha_fin.date()).days)`.
  2. **Estado del recurso en catálogo:**
     - Si `danos_detectados == False`: el recurso pasa a **`DISPONIBLE`**.
     - Si `danos_detectados == True`: el recurso pasa automáticamente a **`MANTENIMIENTO`**.
  3. **Impacto en reputación (`identidad_reputacion`):**
     - Si `danos_detectados == True`: aplica sanción **`DANO_PARCIAL`** (-100 pts) con el detalle de la observación técnica.
     - Si `dias_retraso > 0`: aplica sanción **`TARDANZA`** (-20 pts base y -5 pts por cada día de retraso).
     - Si `dias_retraso == 0` y `danos_detectados == False`: premia al usuario con **`premiar_devolucion_puntual`** (+15 pts).

### Política 4: Prórroga / Renovación (`solicitar_prorroga` y `renovar`)
- Un préstamo solo es apto para renovación si su estado es `ACTIVO` o `ENTREGADO`, los días solicitados son mayores a 0 y la fecha actual aún no ha superado `fecha_fin` (`fecha_actual <= fecha_fin`).
- Al renovarse extiende `fecha_fin` en 7 días. *(Punto a comentar con la profesora el jueves: si en la versión final se mantiene habilitado para el estudiante o solo para gestión cuando no exista cola de espera).*

---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/prestamos/domain/`)
- **`entities/prestamo.py` (`Prestamo`)**:
  - `marcar_entregado()`: Pasa de `ACTIVO` a `ENTREGADO`.
  - `calcular_dias_retraso(fecha_referencia)` y `devolver(fecha_devolucion)`: Cambia el estado a `DEVUELTO` y retorna los días de mora.
  - `solicitar_prorroga(dias, fecha_actual)` y `renovar(dias, fecha_actual)`: Validan vigencia y extienden `fecha_fin`.
- **`entities/garantia.py` (`Garantia`)** y **`value_objects/compromiso_responsabilidad.py` (`CompromisoResponsabilidad`)**:
  - Validan la firma, el testigo y gestionan el estado de la garantía (`PENDIENTE` → `REGISTRADA` → `LIBERADA` / `EJECUTADA`).
- **`entities/checklist.py` (`Checklist`)**:
  - `agregar_item(observaciones, fotos_urls)` y `confirmar()` (`completo = True`). Soporta `TipoChecklist.ESTADO_INICIAL` y `TipoChecklist.ESTADO_DEVOLUCION`.

### Capa de Aplicación (`contexts/prestamos/application/`)
- **`prestamo_service.py` (`PrestamoService`)**:
  - `solicitar_prestamo(...)`: Valida disponibilidad en `RecursoRepository`, guarda el `Prestamo` y cambia el recurso a `EN_USO`.
  - `completar_entrega(...)` (y los pasos `iniciar_entrega`, `agregar_item_checklist`, `confirmar_entrega`, `finalizar_entrega`): Ejecutan el ciclo completo de garantía + checklist inicial y premian puntualidad.
  - `procesar_devolucion(id_prestamo, observaciones_retorno, fotos_urls, danos_detectados)`: Registra la devolución, guarda el checklist de retorno, actualiza el estado del recurso (`DISPONIBLE` o `MANTENIMIENTO`) y llama a `ReputacionService`.
  - `consultar_inspecciones(id_prestamo)`: Devuelve el resumen de garantía, checklist inicial y checklist de devolución.

### Capa de Presentación y Frontend
- **`presentation/prestamo_controller.py`**:
  - Endpoints bajo `/prestamos`: `/entrega/completar`, `/inspeccion`, `/devolucion` (protegido con `require_roles`), `/renovar`, `/usuarios/{id}/historial` y `GET /prestamos` (listado global para gestión).
- **`frontend/src/features/prestamos/pages/HistorialPage.jsx`**:
  - Ventanilla de préstamos con filtro por estado, formulario modal de **Inspección de Salida y Garantía**, formulario modal de **Inspección de Retorno con detección de daños**, y visor de **Checklist y Garantía**.
