# Contexto 2: Catálogo de Recursos (`catalogo`)

**Responsable:** Integrante 2 (Rodrigo)  
**Backend:** `backend/src/prestamos_recursos/contexts/catalogo/`  
**Frontend:** `frontend/src/features/catalogo/`  
**Schema BD:** `catalogo`

---

## 1. Qué se implementó en este contexto

1. **Gestión completa de recursos (`Recurso`):**
   - Creación de nuevos recursos institucionales (equipos de cómputo, multimedia, laboratorio y libros).
   - Búsqueda por texto libre (`filtro`) que filtra por nombre, descripción o categoría.
   - Actualización de los datos del recurso y su ficha técnica (`PUT /recursos/{id_recurso}`).
2. **Ficha Técnica como Value Object (`FichaTecnica`):**
   - Cada recurso almacena sus especificaciones físicas: `marca`, `modelo`, `numero_serie` (único en base de datos), `color`, `estado_fisico` y `foto_url`.
   - Endpoint específico para consultar la ficha técnica detallada (`GET /recursos/{id_recurso}/ficha-tecnica`).
3. **Control de Disponibilidad y Estados Operativos (`EstadoRecurso`):**
   - Consulta de disponibilidad inmediata (`GET /recursos/{id_recurso}/disponibilidad`).
   - Cambio de estado operativo (`PATCH /recursos/{id_recurso}/estado`) entre `DISPONIBLE`, `EN_USO`, `MANTENIMIENTO` y `FUERA_DE_SERVICIO`.
4. **Interfaz de usuario (`/recursos`):**
   - Buscador con filtro en tiempo real, listado de tarjetas con insignias de color según el estado, panel lateral de ficha técnica con fotografía, enlace directo para reservar el recurso (`/reservas?recursoId=...`) disponible exclusivamente para roles solicitantes (oculto para roles de gestión por segregación de funciones, Spec 006), formulario de alta de recursos y selector de cambio de estado para personal de gestión.


---

## 2. Políticas y Reglas de Negocio del Módulo

### Política 1: Integridad de Datos y Ficha Técnica Obligatoria
- Ningún recurso puede existir con nombre vacío, categoría vacía o sin una `FichaTecnica` válida (`ficha_tecnica.es_valida()`).
- En la ficha técnica son obligatorios: `marca`, `modelo`, `numero_serie` y `estado_fisico` (no pueden ser cadenas vacías).
- El `numero_serie` tiene restricción `UNIQUE` en la tabla `catalogo.recursos` para impedir duplicar el mismo bien físico.

### Política 2: Ciclo de Estados Operativos (`EstadoRecurso`)
Todo recurso se encuentra siempre en uno de estos 4 estados:
- **`DISPONIBLE`**: El recurso está en almacén y en condiciones óptimas para ser reservado y prestado.
- **`EN_USO`**: El recurso tiene un préstamo activo/entregado en curso.
- **`MANTENIMIENTO`**: El recurso no puede prestarse porque está en revisión técnica (por ejemplo, cuando en la devolución de un préstamo se reportan daños físicos).
- **`FUERA_DE_SERVICIO`**: El recurso fue dado de baja o presenta daño irreparable.

### Política 3: Regla de Disponibilidad y Conexión con Préstamos y Reservas (Spec 007)
- Un recurso solo reporta `disponible = True` cuando su estado es exactamente `EstadoRecurso.DISPONIBLE` (`recurso.esta_disponible()`).
- **Validación del estado operativo al reservar (Spec 007):**
  - Al solicitar una reserva, `ReservaService` consulta a `RecursoApplicationService`. Se admiten solicitudes de reserva si el recurso está en **`DISPONIBLE`** o **`EN_USO`** (en este último caso para fechas futuras o cola de espera).
  - Si el recurso está en **`MANTENIMIENTO`** o **`FUERA_DE_SERVICIO`**, el sistema rechaza la reserva con `409 Conflict` (`"el recurso no admite reservas por encontrarse en mantenimiento o fuera de servicio"`).
- **Ventana de inicio de préstamo:** La conversión de reserva confirmada en préstamo se realiza dentro de la ventana `fecha_inicio - 1 hora <= ahora <= fecha_fin` (`409 Conflict` fuera de ventana).
- **Transiciones automáticas desde el contexto `prestamos`:**
  - Cuando un gestor convierte una reserva en préstamo (`PrestamoService.solicitar_prestamo`), verifica que el recurso esté en catálogo y lo pasa a **`EN_USO`**.
  - Cuando se procesa la devolución (`PrestamoService.procesar_devolucion`):
    - Si no se detectaron daños (`danos_detectados == False`): el recurso vuelve a **`DISPONIBLE`** y la garantía asociada se libera automáticamente (`LIBERADA` con `fecha_liberacion`).
    - Si se detectaron daños físicos (`danos_detectados == True`): el recurso pasa automáticamente a **`MANTENIMIENTO`** y la garantía queda retenida (`RETENIDA`).
  - Cuando un préstamo en estado `ACTIVO` (aún no entregado físicamente) es cancelado en ventanilla (`PrestamoService.cancelar_prestamo`), el recurso vuelve automáticamente de `EN_USO` a **`DISPONIBLE`** sin penalizar la reputación (Spec 006).

---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/catalogo/domain/`)
- **`entities/recurso.py` (`Recurso`)**:
  - `__post_init__()`: Valida que `nombre` y `categoria` no estén vacíos y que `ficha_tecnica` sea instancia de `FichaTecnica`.
  - `esta_disponible() -> bool`: Devuelve `True` únicamente si `self.estado == EstadoRecurso.DISPONIBLE`.
  - `cambiar_estado(nuevo_estado: EstadoRecurso)`: Valida que el nuevo estado sea un `EstadoRecurso` válido y actualiza la entidad.
- **`value_objects/ficha_tecnica.py` (`FichaTecnica`)**:
  - Value Object inmutable (`@dataclass(frozen=True)`) con el método `es_valida()` que exige `marca`, `modelo`, `numero_serie` y `estado_fisico`.
- **`enums/estado_recurso.py` (`EstadoRecurso`)**:
  - Define los 4 estados: `DISPONIBLE`, `EN_USO`, `MANTENIMIENTO`, `FUERA_DE_SERVICIO`.
- **`repositories/recurso_repository.py` (`RecursoRepository`)**:
  - Contrato abstracto del repositorio (`guardar`, `obtener_por_id`, `buscar`, `actualizar_estado`).

### Capa de Aplicación (`contexts/catalogo/application/`)
- **`services.py` (`RecursoApplicationService`)**:
  - `crear_recurso(...)`: Construye el Value Object `FichaTecnica`, valida `es_valida()`, instancia la entidad `Recurso` en estado `DISPONIBLE` y la guarda en el repositorio.
  - `buscar(filtro)`: Devuelve la lista de `RecursoDTO` que coinciden con el término buscado.
  - `consultar_disponibilidad(id_recurso)` y `obtener_ficha_tecnica(id_recurso)`.
  - `actualizar_recurso(...)` y `actualizar_estado(id_recurso, nuevo_estado)`.

### Capa de Infraestructura (`contexts/catalogo/infrastructure/`)
- **`models/recurso_model.py` (`RecursoModel`)**: Modelo SQLAlchemy mapeado a la tabla `catalogo.recursos`.
- **`repositories/sql_recurso_repository.py` (`SqlRecursoRepository`)**: Implementa las consultas SQL (incluyendo `ILIKE` para búsqueda por nombre, descripción o categoría) usando `session.flush()` conforme a la política de transacciones D13.

### Capa de Presentación y Frontend
- **`presentation/recurso_controller.py`**:
  - `GET /recursos` (búsqueda), `POST /recursos` (crear), `GET /recursos/{id}/disponibilidad`, `GET /recursos/{id}/ficha-tecnica`, `PUT /recursos/{id}` y `PATCH /recursos/{id}/estado`.
- **`frontend/src/features/catalogo/pages/BuscarRecursosPage.jsx`**:
  - Carga el catálogo y el perfil del usuario. Si el usuario tiene rol `GESTOR_ALMACEN` o `ADMINISTRADOR_SISTEMA`, habilita el formulario **"Registrar nuevo recurso"** y el selector **"Cambiar estado operativo"**, y oculta el bloque de solicitud de reserva por segregación de funciones. Para usuarios con rol solicitante (`!esGestion`), muestra el botón «Solicitar Reserva de este Recurso» que redirige a `/reservas?recursoId=...` cuando el recurso está en `DISPONIBLE` o `EN_USO` (indicando una nota si está en uso sobre fechas futuras / lista de espera), y muestra alerta de aviso si está en `MANTENIMIENTO` o `FUERA_DE_SERVICIO` (Spec 007).

