# Análisis Técnico del Contexto: Reservas (Rama `feature/reservas-johan`)

Como Arquitecto de Software, a continuación se presenta el análisis técnico detallado del código implementado en la rama `feature/reservas-johan` para el contexto de **Reservas**, así como sus dependencias con el contexto de **Catálogo** y los requerimientos de integración bajo los principios de Domain-Driven Design (DDD).

---

## 1. Estado del Contexto (Reservas)

### Entidades y Objetos de Dominio
- **Entidad (Aggregate Root) `Reserva`** (`backend/src/prestamos_recursos/contexts/reservas/domain/entities/reserva.py`):
  - Atributos: `id`, `usuario_id`, `recurso_id`, `fecha_inicio`, `fecha_fin`, `estado` (`EstadoReserva`).
  - Lógica de negocio encapsulada:
    - Validación de fechas (`__post_init__`): La fecha de fin debe ser posterior a la fecha de inicio.
    - Método de fábrica `crear(...)`.
    - Transiciones de estado: `cancelar()` y `convertir_a_prestamo()`.
    - Reglas de vigencia (`esta_vigente()`) y cruce de horarios (`se_superpone_con(...)`).
- **Enumeración `EstadoReserva`** (`backend/src/prestamos_recursos/contexts/reservas/domain/enums/estado_reserva.py`):
  - Estados posibles: `PENDIENTE`, `CONFIRMADA`, `CANCELADA`, `VENCIDA`, `CONVERTIDA`.

### Servicios de Dominio
- **`AlgoritmoPrioridadService`** (`backend/src/prestamos_recursos/contexts/reservas/domain/services/algoritmo_prioridad_service.py`):
  - Ordena la cola de espera de reservas según la proximidad de la fecha de inicio (`calcular_prioridad`).

### Repositorios y Modelos de Infraestructura
- **Interfaz `ReservaRepository`** (`backend/src/prestamos_recursos/contexts/reservas/domain/repositories/reserva_repository.py`): Contrato de dominio para persistencia.
- **`MemoriaReservaRepository`** / **`SqlReservaRepository`** (`backend/src/prestamos_recursos/contexts/reservas/infrastructure/repositories/`):
  - `SqlReservaRepository` implementa parcialmente la consulta de reservas activas por recurso (`obtener_activas_por_recurso`).
- **`ReservaModel`** (`backend/src/prestamos_recursos/contexts/reservas/infrastructure/models/reserva_model.py`): Modelo SQLAlchemy mapeado al esquema `reservas.reservas`.

### Servicios de Aplicación y DTOs
- **`ReservaService`** (`backend/src/prestamos_recursos/contexts/reservas/application/reserva_service.py`):
  - `crear_reserva(datos: CrearReservaDTO)`: Valida superposición de horarios contra reservas activas del mismo recurso.
  - `obtener_reserva(id_reserva: UUID)`
  - `cancelar_reserva(id_reserva: UUID)`
  - `convertir_a_prestamo(id_reserva: UUID)` (Actualmente lanza `NotImplementedError`).
  - `obtener_cola_espera(id_recurso: UUID)`
- **DTOs** (`backend/src/prestamos_recursos/contexts/reservas/application/dto/reserva_dto.py`):
  - `CrearReservaDTO` (con validadores de zona horaria y rango de fechas).
  - `ReservaDTO` (para respuesta estructurada).

### Endpoints (Presentación / FastAPI)
- **`ReservaController`** (`backend/src/prestamos_recursos/contexts/reservas/presentation/reserva_controller.py` - Prefijo `/reservas`):
  - `POST /reservas` (`solicitar_reserva`): Crea una nueva reserva (Código 201 o 409 si hay conflicto).
  - `GET /reservas/{id_reserva}` (`consultar_reserva`): Obtiene una reserva por ID (Código 200 o 404).
  - `PATCH /reservas/{id_reserva}/cancelar` (`cancelar_reserva`): Cancela una reserva existente.
  - `GET /reservas/recurso/{id_recurso}/cola` (`consultar_cola`): Consulta la cola de espera de un recurso.

---

## 2. Dependencias Externas con el Contexto de "Catálogo"

El contexto de Reservas opera actualmente de forma desacoplada en cuanto a persistencia, pero hace referencia estricta a la identidad de los recursos mediante el atributo `recurso_id`. Las partes exactas del código donde se interactúa o se espera validar contra Catálogo son:

1. **Entidad de Dominio (`Reserva`)**:
   - Atributo `recurso_id: UUID` (`backend/src/prestamos_recursos/contexts/reservas/domain/entities/reserva.py` línea 18).
   - En el método `se_superpone_con(self, otra: Reserva)`, se valida que `self.recurso_id == otra.recurso_id`. Sin embargo, **no existe ninguna validación en el dominio** que garantice que el `recurso_id` provisto corresponda a un recurso existente y válido en el catálogo.

2. **Servicio de Aplicación (`ReservaService`)**:
   - En `crear_reserva(self, datos: CrearReservaDTO)` (`backend/src/prestamos_recursos/contexts/reservas/application/reserva_service.py` línea 25-34), se invoca `self._reserva_repository.obtener_activas_por_recurso(reserva.recurso_id)`.
   - **Falta crítica de integración**: El servicio de aplicación **asume** que el `recurso_id` recibido es válido. No verifica si el recurso existe, si está activo, ni si permite reservas según las reglas del Catálogo.

3. **Controlador y DTOs (`ReservaController` y `CrearReservaDTO`)**:
   - `CrearReservaDTO` recibe `recurso_id: UUID` sin validación previa contra el inventario/catálogo.
   - `GET /reservas/recurso/{id_recurso}/cola` consulta la cola de un recurso sin verificar si dicho recurso existe en el sistema.

4. **Frontend (`frontend/src/features/reservas/api.js`)**:
   - La función `solicitarReserva(idUsuario, idRecurso)` envía solicitudes de reserva asociadas a un recurso del catálogo.

---

## 3. Requerimientos para Catálogo (Para Integración DDD)

Para respetar los principios de Domain-Driven Design (DDD) y permitir que el contexto de **Reservas** se integre correctamente con **Catálogo** sin romper la encapsulación ni realizar consultas directas entre bases de datos de diferentes contextos, **se deben construir** en la carpeta `catalogo` (`backend/src/prestamos_recursos/contexts/catalogo/`) los siguientes componentes:

### A. Métodos de Servicio Interno (Application Layer)
En `backend/src/prestamos_recursos/contexts/catalogo/application/recurso_service.py`, implementar:

1. **`obtener_recurso(id_recurso: UUID) -> RecursoDTO`** (o equivalente):
   - Permite consultar la información detallada de un recurso por su ID. Si no existe, debe lanzar una excepción controlada (ej. `LookupError` o `RecursoNoEncontradoException`).
2. **`consultar_disponibilidad(id_recurso: UUID) -> bool`** (Ya declarada pero pendiente):
   - Retorna `True` si el recurso existe y se encuentra en un estado que permite ser reservado/prestado (ej. `EstadoRecurso.DISPONIBLE`).
3. **`verificar_existencia_y_disponibilidad(id_recurso: UUID) -> None`** (Método auxiliar recomendado para aplicación):
   - Lanza una excepción (`ValueError` o `LookupError`) si el recurso no existe o no está disponible para reserva, facilitando que `ReservaService` valide la precondición antes de persistir una reserva.

### B. Endpoints de API (Presentation / FastAPI)
En `backend/src/prestamos_recursos/contexts/catalogo/presentation/recurso_controller.py` (con prefijo `/recursos`), implementar:

1. **`GET /recursos` (`buscar_recursos`)**:
   - Parámetro de consulta: `filtro: str = ""`
   - Respuesta: Lista de recursos (`list[RecursoDTO]`) que coincidan con el filtro.
2. **`GET /recursos/{id_recurso}` (`obtener_recurso_por_id`)** (Requerido para validación y UI):
   - Parámetro de ruta: `id_recurso: UUID`
   - Respuesta: `RecursoDTO` (Código 200 o 404 si no existe).
3. **`GET /recursos/{id_recurso}/disponibilidad` (`consultar_disponibilidad`)**:
   - Parámetro de ruta: `id_recurso: UUID`
   - Respuesta: Objeto JSON con el estado de disponibilidad (ej. `{"disponible": true}`).
4. **`GET /recursos/{id_recurso}/ficha-tecnica` (`obtener_ficha_tecnica`)**:
   - Parámetro de ruta: `id_recurso: UUID`
   - Respuesta: Ficha técnica detallada del recurso.
