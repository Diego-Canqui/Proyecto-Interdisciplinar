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
2. **Flujo de Entrega Física y Cancelación en Ventanilla (`Garantia` + `Checklist` de salida, Spec 006):**
   - Mientras el préstamo está en estado `ACTIVO` (aún en ventanilla y no entregado físicamente), el gestor puede formalizar la entrega o **cancelar el préstamo en ventanilla** (`POST /prestamos/{id}/cancelar`) si el solicitante no asiste o desiste, pasando el préstamo a `CANCELADO` y liberando el recurso a `DISPONIBLE` en el catálogo sin penalizar la reputación.
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
- **`CANCELADO`**: Cancelado en ventanilla mientras estaba en estado `ACTIVO` o administrativamente antes de la entrega física.

### Política 2: Requisitos de Entrega Física y Cancelación en Ventanilla (Spec 006)
- Solo un préstamo en estado `ACTIVO` puede iniciar y completar el proceso de entrega o ser cancelado en ventanilla.
- **Cancelación de préstamo en ventanilla (`POST /prestamos/{id}/cancelar`):**
  - Si el prestatario no se presenta o desiste de recoger el recurso, el personal de gestión ejecuta la cancelación.
  - El préstamo pasa a estado `CANCELADO` y el recurso en el catálogo pasa automáticamente de `EN_USO` a **`DISPONIBLE`** sin aplicar sanciones en reputación.
  - Si el préstamo ya está en estado `ENTREGADO`, `DEVUELTO`, `VENCIDO` o `CANCELADO`, la operación se rechaza con `409 Conflict` (un bien ya entregado debe registrarse como devolución).
- **Formalización de entrega (`completar_entrega`):**
  - Para marcar un préstamo como `ENTREGADO` es obligatorio:
    1. Que exista un `Checklist` de tipo `ESTADO_INICIAL` confirmado (`checklist.completo == True`).
    2. Que exista una `Garantia` asociada en estado `REGISTRADA` con un `CompromisoResponsabilidad` válido (`contenido`, `firma_url` y `testigo` no vacíos).
  - **Premio por recogida puntual:** Si la fecha de entrega es menor o igual a la fecha de inicio pactada (`hoy <= fecha_inicio`), se invoca `reputacion_service.premiar_entrega_puntual(usuario_id)` (+10 pts).

### Política 3: Recepción Física, Retrasos, Daños y Ciclo de Vida de la Garantía (Spec 007)
- Solo el personal de gestión (`GESTOR_ALMACEN` y `ADMINISTRADOR_SISTEMA`) puede registrar la devolución (`POST /prestamos/{id}/devolucion`).
- **Segregación de acciones en UI (Spec 006):** En la pantalla `/historial`, el botón «📥 Registrar Devolución» únicamente se muestra cuando el préstamo se encuentra en estado `ENTREGADO` o `VENCIDO`. Para préstamos en estado `ACTIVO`, se muestran exclusivamente «📋 Realizar Entrega» y «✕ Cancelar Préstamo».
- Un préstamo ya `DEVUELTO` o `CANCELADO` no puede volver a devolverse (responde `409 Conflict`).
- Al procesar la devolución (`procesar_devolucion`):
  1. **Cálculo de retraso (`calcular_dias_retraso`):** `max(0, (fecha_devolucion.date() - fecha_fin.date()).days)`.
  2. **Estado del recurso y ciclo de vida de la garantía:**
     - Si `danos_detectados == False`:
       - El recurso vuelve a **`DISPONIBLE`**.
       - La garantía asociada pasa automáticamente a **`LIBERADA`** y se registra su `fecha_liberacion`.
     - Si `danos_detectados == True`:
       - El recurso pasa automáticamente a **`MANTENIMIENTO`**.
       - La garantía asociada pasa a **`RETENIDA`** (`fecha_liberacion = None`).
  3. **Impacto en reputación (`identidad_reputacion`):**
     - Si `danos_detectados == True`: aplica sanción **`DANO_PARCIAL`** (-30 pts, deuda $50, bloqueo 30 días) o **`DANO_TOTAL`** (-100 pts, deuda = valor del recurso, bloqueo 60 días).
     - Si `dias_retraso > 0`: aplica sanción **`TARDANZA`** (-10 pts, deuda $0, gracia 1 día; desde el 2º día, bloqueo 1:1 en días).
     - Si `dias_retraso == 0` y `danos_detectados == False`: premia al usuario con **`premiar_devolucion_puntual`** (**+10 puntos**, tope 1000).

### Política 4: Prórroga / Renovación (`solicitar_prorroga` y `renovar`)
- Un préstamo solo es apto para renovación si su estado es `ACTIVO` o `ENTREGADO`, los días solicitados son mayores a 0 y la fecha actual aún no ha superado `fecha_fin` (`fecha_actual <= fecha_fin`).
- Al renovarse extiende `fecha_fin` en 7 días.
- **Actualización Spec 006:** Se retiró el botón libre de renovación «+7 días» de la interfaz de `/historial` para impedir extensiones unilaterales sin control institucional, manteniendo el método de dominio y el endpoint de backend por compatibilidad con la suite de pruebas.

### Política 5: Horario de Atención y Ventana de Conversión (Spec 007)
- **Horario de atención institucional:** Las entregas y devoluciones físicas en ventanilla de almacén se realizan de lunes a viernes entre las **08:00 y las 20:00 UTC** inclusive.
- **Ventana operativa de conversión:** Un préstamo solo puede iniciarse a partir de una reserva confirmada dentro del intervalo `fecha_inicio - 1 hora <= ahora <= fecha_fin` (`409 Conflict` fuera de dicha ventana).


---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/prestamos/domain/`)
- **`entities/prestamo.py` (`Prestamo`)**:
  - `marcar_entregado()`: Pasa de `ACTIVO` a `ENTREGADO`.
  - `cancelar(motivo)`: Exige estrictamente estado `ACTIVO`; pasa a `CANCELADO` (Spec 006). Si ya fue entregado o devuelto, lanza `ValueError`.
  - `calcular_dias_retraso(fecha_referencia)` y `devolver(fecha_devolucion)`: Cambia el estado a `DEVUELTO` y retorna los días de mora.
  - `solicitar_prorroga(dias, fecha_actual)` y `renovar(dias, fecha_actual)`: Validan vigencia y extienden `fecha_fin`.
- **`entities/garantia.py` (`Garantia`)** y **`value_objects/compromiso_responsabilidad.py` (`CompromisoResponsabilidad`)**:
  - Validan la firma, el testigo y gestionan el ciclo de vida de la garantía: nace en `REGISTRADA` con `fecha_registro`, pasa a `LIBERADA` con `fecha_liberacion` mediante `liberar()` cuando no hay daños, o a `RETENIDA` (`fecha_liberacion = None`) mediante `retener()` ante daños físicos (Spec 007).
- **`entities/checklist.py` (`Checklist`)**:
  - `agregar_item(observaciones, fotos_urls)` y `confirmar()` (`completo = True`). Soporta `TipoChecklist.ESTADO_INICIAL` y `TipoChecklist.ESTADO_DEVOLUCION`.

### Capa de Aplicación (`contexts/prestamos/application/`)
- **`prestamo_service.py` (`PrestamoService`)**:
  - Desacoplamiento DDD con `catalogo_service: RecursoApplicationService` inyectado para validar y transicionar estados en catálogo.
  - `solicitar_prestamo(...)`: Valida existencia en catálogo, guarda el `Prestamo` y cambia el recurso a `EN_USO`.
  - `cancelar_prestamo(id_prestamo, motivo)`: Cancela un préstamo `ACTIVO`, guarda el cambio y libera automáticamente el recurso en catálogo a `DISPONIBLE` sin sancionar la reputación (Spec 006).
  - `contar_prestamos_en_curso(id_usuario)`: Cuenta cuántos préstamos del usuario se encuentran en estado `ACTIVO`, `ENTREGADO` o `VENCIDO` para el límite de operaciones simultáneas y la eliminación segura de usuarios (Spec 006).
  - `completar_entrega(...)` (y los pasos `iniciar_entrega`, `agregar_item_checklist`, `confirmar_entrega`, `finalizar_entrega`): Ejecutan el ciclo completo de garantía + checklist inicial y premian puntualidad (+10 pts).
  - `procesar_devolucion(id_prestamo, observaciones_retorno, fotos_urls, danos_detectados)`: Registra la devolución, guarda el checklist de retorno, actualiza el estado del recurso (`DISPONIBLE` o `MANTENIMIENTO`), libera o retiene la garantía (`garantia.liberar()` o `garantia.retener()`), y llama a `ReputacionService` (Spec 007).
  - `consultar_inspecciones(id_prestamo)`: Devuelve el resumen de garantía (incluyendo `fecha_liberacion`), checklist inicial y checklist de devolución.

### Capa de Infraestructura (`contexts/prestamos/infrastructure/`)
- **`repositories/sql_checklist_repository.py`**, **`sql_garantia_repository.py`** y **`sql_prestamo_repository.py`**:
  - Implementan `session.flush()` (D13) y aseguran la copia de listas en colecciones mutables (como `fotos_urls`) para garantizar la persistencia íntegra de inspecciones y garantías en PostgreSQL y SQLite (Spec 006).

### Capa de Presentación y Frontend
- **`presentation/prestamo_controller.py`**:
  - Endpoints bajo `/prestamos`: `/entrega/completar`, `/inspeccion`, `/devolucion` (protegido con `require_roles`), `POST /{id_prestamo}/cancelar` (cancelación en ventanilla para gestión, Spec 006), `/renovar`, `/usuarios/{id}/historial` y `GET /prestamos` (listado global para gestión).
- **`frontend/src/features/prestamos/pages/HistorialPage.jsx`**:
  - Ventanilla de préstamos con acciones segregadas por estado (en `ACTIVO` muestra «📋 Realizar Entrega» y «✕ Cancelar Préstamo»; en `ENTREGADO` y `VENCIDO` muestra «📥 Registrar Devolución»), filtro por estado incluyendo `CANCELADO`, desplazamiento automático (`scrollIntoView`) al abrir paneles, formulario modal de **Inspección de Salida y Garantía**, formulario de **Inspección de Retorno con detección de daños**, y visor de **Checklist y Garantía** mostrando `Fecha liberación` si fue liberada (Spec 007).

