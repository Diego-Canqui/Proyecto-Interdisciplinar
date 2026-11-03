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
- Ningún recurso puede crearse sin una `FichaTecnica` válida (`ficha_tecnica.es_valida()`, validada en `RecursoApplicationService.crear_recurso`; si no lo es, el endpoint responde `400`). Hoy `nombre` y `categoria` son obligatorios solo como campos requeridos del DTO (pueden llegar como cadena vacía): validarlos en el dominio es una mejora pendiente.
- En la ficha técnica son obligatorios: `marca`, `modelo`, `numero_serie` y `estado_fisico` (no pueden ser cadenas vacías).
- El `numero_serie` tiene restricción `UNIQUE` en la tabla `catalogo.recursos` para impedir duplicar el mismo bien físico.

### Limitación conocida: criterios de inspección por tipo de recurso
- El catálogo todavía no expone qué se debe inspeccionar de cada recurso. El checklist de entrega de `prestamos` usa 4 casillas fijas (carcasa, pantalla, cables/cargador, nº de serie), pensadas para equipos de cómputo, y también aparecen al entregar un libro.
- **Tarea futura (catálogo + préstamos):** añadir a la ficha (`FichaTecnica`/`RecursoDTO`) una lista de criterios de inspección según la categoría (`Cómputo`, `Multimedia`, `Laboratorio`, `Libros`) para que el frontend de `prestamos` genere las casillas dinámicamente.

### Política 2: Ciclo de Estados Operativos (`EstadoRecurso`)
Todo recurso se encuentra siempre en uno de estos 4 estados:
- **`DISPONIBLE`**: El recurso está en almacén y en condiciones óptimas para ser reservado y prestado.
- **`EN_USO`**: El recurso tiene un préstamo activo/entregado en curso.
- **`MANTENIMIENTO`**: El recurso no puede prestarse porque está en revisión técnica (por ejemplo, cuando en la devolución de un préstamo se reportan daños físicos).
- **`FUERA_DE_SERVICIO`**: El recurso fue dado de baja o presenta daño irreparable.

### Política 3: Regla de Disponibilidad y Conexión con Préstamos
- Un recurso solo se puede reservar y prestar cuando su estado es exactamente `EstadoRecurso.DISPONIBLE`. `PrestamoService.solicitar_prestamo` lo verifica y el endpoint `GET /recursos/{id}/disponibilidad` devuelve `disponible = (estado == DISPONIBLE)`.
- **Transiciones automáticas desde el contexto `prestamos`:**
  - Cuando un gestor convierte una reserva en préstamo (`PrestamoService.solicitar_prestamo`), verifica que el recurso esté `DISPONIBLE` y lo pasa automáticamente a **`EN_USO`**.
  - Cuando se procesa la devolución (`PrestamoService.procesar_devolucion`), si no se detectaron daños vuelve a **`DISPONIBLE`**; si se detectaron daños físicos (`danos_detectados = True`), pasa automáticamente a **`MANTENIMIENTO`**.
  - Cuando un préstamo en estado `ACTIVO` (aún no entregado físicamente) es cancelado en ventanilla (`PrestamoService.cancelar_prestamo`), el recurso vuelve automáticamente de `EN_USO` a **`DISPONIBLE`** sin alterar la reputación (Spec 006).

---

## 3. Guía de Código que debes dominar para la exposición

### Capa de Dominio (`contexts/catalogo/domain/`)
- **`entities/recurso.py` (`Recurso`)**:
  - Dataclass del Aggregate Root con `nombre`, `descripcion`, `categoria`, `estado` y `ficha_tecnica`.
  - `marcar_disponible()`: Pone el recurso en `DISPONIBLE`; lanza `ValueError` si está `FUERA_DE_SERVICIO`.
  - `marcar_no_disponible()`: Pone el recurso en `EN_USO`.
  - `actualizar_estado(nuevo_estado: EstadoRecurso)`: Valida (`TypeError`) que sea un `EstadoRecurso` y actualiza la entidad.
  - La validación de que `nombre`, `categoria` y la ficha sean válidos se hace en `RecursoApplicationService.crear_recurso` (con `FichaTecnica.es_valida()`).
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
  - Carga el catálogo y el perfil del usuario. Si el usuario tiene rol `GESTOR_ALMACEN` o `ADMINISTRADOR_SISTEMA`, habilita el formulario **"Registrar nuevo recurso"** y el selector **"Cambiar estado operativo"**, y oculta el bloque de solicitud de reserva por segregación de funciones. Para usuarios con rol solicitante (`!esGestion`), muestra el botón «Solicitar Reserva de este Recurso» que redirige a `/reservas?recursoId=...` (Spec 006).

