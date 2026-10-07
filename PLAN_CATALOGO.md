# PLAN_CATALOGO.md - Guía de Desarrollo del Contexto "Catálogo"

Este documento establece la guía técnica y arquitectónica para el desarrollo del **Contexto Acotado de Catálogo** dentro del Sistema de Gestión de Préstamos de Recursos, aplicando los principios de Domain-Driven Design (DDD), FastAPI (Python), SQLAlchemy y React (Vite).

---

## 1. Visión General del Contexto "Catálogo"

El **Contexto de Catálogo** es el encargado de gestionar el inventario maestro de todos los ítems físicos y recursos institucionales disponibles para préstamo (equipos electrónicos, libros, herramientas, salas, etc.).

### Responsabilidades principales:
- Registro, actualización y baja de recursos físicos en el sistema.
- Gestión de especificaciones técnicas detalladas (`FichaTecnica`).
- Control de estados operativos e inventario (`EstadoRecurso`).
- Exposición de servicios de consulta de disponibilidad y características técnicas para los demás contextos del sistema.

### Límites del Contexto (Bounded Context Limits):
- **NO** gestiona usuarios, autenticación ni perfiles de reputación (responsabilidad de `identidad_reputacion`).
- **NO** gestiona solicitudes de reserva ni colas de prioridad (responsabilidad de `reservas`).
- **NO** gestiona la entrega, devolución ni plazos de préstamos activos (responsabilidad de `prestamos`).
- Cualquier interacción con otros contextos se realiza estrictamente mediante identificadores únicos (`recurso_id`) y a través de los servicios de la capa de aplicación.

---

## 2. Modelos de Dominio (Domain Layer)

Ubicación: `backend/src/prestamos_recursos/contexts/catalogo/domain/`

### 2.1. Agregado Root: `Recurso`
Representa la unidad gestionada en el inventario.
- **Atributos:**
  - `id`: `UUID` (Identificador único universal)
  - `nombre`: `str` (Nombre descriptivo del recurso)
  - `descripcion`: `str` (Detalle general del ítem)
  - `categoria`: `str` (Clasificación, ej. "Electrónica", "Bibliografía")
  - `estado`: `EstadoRecurso` (Enum operativo)
  - `ficha_tecnica`: `FichaTecnica` (Value Object con detalles técnicos)
- **Invariantes y Métodos de Dominio:**
  - `marcar_disponible()`: Restaura el estado a disponible (falla si está fuera de servicio).
  - `marcar_no_disponible()`: Cambia el estado a en uso.
  - `actualizar_estado(nuevo_estado)`: Valida la transición y actualiza el estado.

### 2.2. Value Object: `FichaTecnica`
Agrupa las características técnicas inmutables del recurso.
- **Atributos:**
  - `marca`: `str`
  - `modelo`: `str`
  - `numero_serie`: `str`
  - `color`: `str`
  - `estado_fisico`: `str` (Ej. "Excelente", "Bueno", "Dañado")
  - `foto_url`: `str` (Enlace a imagen descriptiva)
- **Métodos:**
  - `es_valida()`: Valida que los campos esenciales no estén vacíos.

### 2.3. Enum: `EstadoRecurso`
- `DISPONIBLE`
- `EN_USO`
- `MANTENIMIENTO`
- `FUERA_DE_SERVICIO`

---

## 3. Casos de Uso (Application Layer)

Ubicación: `backend/src/prestamos_recursos/contexts/catalogo/application/services.py`

El servicio de aplicación (`RecursoApplicationService`) coordina las transacciones y reglas de negocio sin contener lógica de dominio pura:

1. **`crear_recurso(...)`**: Registra un nuevo recurso en el catálogo validando su ficha técnica y estableciéndolo inicialmente como `DISPONIBLE`. Retorna el `UUID` creado.
2. **`obtener_por_id(id_recurso)`**: Recupera los datos básicos del recurso en forma de DTO (`RecursoDTO`).
3. **`buscar_disponibles(categoria)`**: Filtra y lista los recursos disponibles en el inventario por categoría opcional.
4. **`actualizar_estado(id_recurso, nuevo_estado)`**: Cambia el estado operativo del recurso tras validar su existencia.
5. **`consultar_disponibilidad(id_recurso)`**: Retorna un booleano (`True`/`False`) indicando si el recurso se encuentra libre para préstamo/reserva.
6. **`obtener_ficha_tecnica(id_recurso)`**: Consulta la información técnica detallada del recurso.

---

## 4. Endpoints de la API (Presentation Layer - FastAPI)

Ubicación: `backend/src/prestamos_recursos/contexts/catalogo/presentation/recurso_controller.py`

Rutas expuestas bajo el prefijo `/recursos`:

- `POST /recursos`
  - **Descripción:** Registra un nuevo recurso en el catálogo.
  - **Payload:** Datos del recurso y ficha técnica.
  - **Respuesta:** `201 Created` con el ID generado.
- `GET /recursos`
  - **Descripción:** Busca y lista recursos aplicando filtros opcionales (ej. `?filtro=laptop&categoria=electronica`).
  - **Respuesta:** `200 OK` con lista de `RecursoDTO`.
- `GET /recursos/{id_recurso}`
  - **Descripción:** Obtiene la información detallada de un recurso específico.
  - **Respuesta:** `200 OK` o `404 Not Found`.
- `GET /recursos/{id_recurso}/disponibilidad`
  - **Descripción:** Consulta rápida de disponibilidad (consumida internamente por otros contextos).
  - **Respuesta:** `200 OK` (`{"disponible": true/false}`).
- `GET /recursos/{id_recurso}/ficha-tecnica`
  - **Descripción:** Obtiene los detalles de la ficha técnica del recurso.
  - **Respuesta:** `200 OK` con especificaciones técnicas.
- `PATCH /recursos/{id_recurso}/estado`
  - **Descripción:** Actualiza el estado operativo del recurso (Ej. mantenimiento, fuera de servicio).
  - **Payload:** `{"nuevo_estado": "MANTENIMIENTO"}`.

---

## 5. Estructura del Frontend (React - Features)

Ubicación: `frontend/src/features/catalogo/`

Estructura modular recomendada:

```text
frontend/src/features/catalogo/
├── index.js                  # Punto de entrada / exportaciones públicas
├── api.js                    # Servicios Axios / cliente HTTP para endpoints de catálogo
├── components/
│   ├── RecursoCard.jsx       # Tarjeta visual de resumen del recurso
│   ├── RecursoFiltros.jsx    # Barra de búsqueda y filtrado por categoría/estado
│   └── FichaTecnicaModal.jsx # Modal para visualizar especificaciones técnicas
├── pages/
│   ├── BuscarRecursosPage.jsx# Vista principal de búsqueda y catálogo público
│   ├── DetalleRecursoPage.jsx# Vista detallada del recurso y su ficha técnica
│   └── GestionRecursosPage.jsx# Vista administrativa para altas y gestión de estados
└── hooks/
    └── useCatalogo.js        # Custom hook para manejo de estado y llamadas a la API de catálogo
```

---

## 6. Interacciones con otros contextos

Para cumplir estrictamente con las reglas de arquitectura desacoplada por Bounded Contexts:

1. **Aislamiento de Clases:**
   - Está **prohibido** importar entidades, modelos SQLAlchemy o lógica interna de `reservas`, `prestamos` o `identidad_reputacion` en el contexto `catalogo`, y viceversa.
   - Las referencias entre contextos se realizan **únicamente mediante IDs (`recurso_id`)**.

2. **Servicios de Aplicación como Contrato:**
   - Cuando el contexto de **Reservas** necesita validar si un recurso existe y está disponible antes de crear una reserva, debe invocar el servicio de aplicación de catálogo (o realizar una llamada HTTP al endpoint de disponibilidad del catálogo):
     ```python
     # Ejemplo conceptual desde otro contexto (vía servicio de aplicación o API client)
     disponible = recurso_application_service.consultar_disponibilidad(recurso_id)
     ```
   - Cuando el contexto de **Préstamos** registra la salida o devolución de un ítem, notifica al catálogo para actualizar su estado (`EN_USO` o `DISPONIBLE`) llamando a `actualizar_estado(recurso_id, nuevo_estado)`.
