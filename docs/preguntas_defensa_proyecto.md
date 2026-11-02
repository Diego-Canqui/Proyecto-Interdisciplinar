# Guía de Defensa de Proyecto — Preguntas Básicas (TI2)

> [!IMPORTANT]
> **Propósito del documento:** Esta guía está dirigida a los 4 integrantes del equipo para preparar la sustentación técnica ante la profesora de TI2. Explica con claridad, precisión técnica y analogías directas las 10 preguntas clave (y preguntas derivadas) que suelen formularse en la defensa de arquitectura y desarrollo de software.

---

## Índice Rápido
1. [¿Cómo se llama su base de datos y qué motor usa?](#1-cómo-se-llama-su-base-de-datos-y-qué-motor-usa)
2. [¿Cómo están organizadas sus tablas? (Esquemas de BD)](#2-cómo-están-organizadas-sus-tablas-esquemas-de-bd)
3. [¿Qué framework usan en el backend (Python) y cómo se ejecuta?](#3-qué-framework-usan-en-el-backend-python-y-cómo-se-ejecuta)
4. [¿Qué framework usan en el frontend (JavaScript)?](#4-qué-framework-usan-en-el-frontend-javascript)
5. [¿Dónde viven los archivos HTML? ¿Existen los archivos HTML? (SPA)](#5-dónde-viven-los-archivos-html-existen-los-archivos-html-spa)
6. [¿Qué arquitectura usan? (DDD + Clean Architecture)](#6-qué-arquitectura-usan-ddd--clean-architecture)
7. [¿Cómo se comunican los 4 módulos de los 4 integrantes?](#7-cómo-se-comunican-los-4-módulos-de-los-4-integrantes)
8. [¿Quién hace el commit en la base de datos? (Unit of Work y Transacciones)](#8-quién-hace-el-commit-en-la-base-de-datos-unit-of-work-y-transacciones)
9. [¿Cómo protegen contraseñas y sesiones? (Bcrypt + JWT)](#9-cómo-protegen-contraseñas-y-sesiones-bcrypt--jwt)
10. [¿Cómo prueban el sistema y aseguran la calidad? (Pytest + Ruff)](#10-cómo-prueban-el-sistema-y-aseguran-la-calidad-pytest--ruff)
11. [Chuleta rápida: «Para responder en 10 segundos»](#11-chuleta-rápida-para-responder-en-10-segundos)

---

## 1. ¿Cómo se llama su base de datos y qué motor usa?

### Respuesta directa:
> *"Usamos el motor relacional **PostgreSQL 16**, ejecutado en un contenedor Docker llamado `prestamos_db`. La base de datos se llama `prestamos_recursos` y el usuario asignado por defecto para la conexión del backend es `prestamos`."*

### Detalles técnicos de soporte:
- **Motor:** PostgreSQL versión 16 (imagen oficial `postgres:16`).
- **Contenedor Docker:** `prestamos_db` (orquestado mediante `docker-compose.yml`).
- **Base de datos:** `prestamos_recursos`.
- **Puerto:** `5432` expuesto al host.
- **Volumen persistente:** `pgdata` (asegura que los datos no se borren al detener el contenedor).
- **Cadena de conexión (DATABASE_URL):**
  ```text
  postgresql+psycopg://prestamos:prestamos@localhost:5432/prestamos_recursos
  ```
  *(Usa el driver moderno `psycopg` v3 con SQLAlchemy 2.0).*

> [!TIP]
> Si la profesora pregunta: *«¿Dónde está configurada esa conexión?»*, respondes:
> *"Las variables residen en el archivo `.env` en la raíz (por seguridad nunca se sube a Git) y son leídas tipadamente por el backend mediante `Pydantic Settings` en `config.py`."*

---

## 2. ¿Cómo están organizadas sus tablas? (Esquemas de BD)

### Respuesta directa:
> *"No tenemos todas las tablas revueltas en el esquema por defecto (`public`). En PostgreSQL creamos **4 esquemas (schemas) lógicos**, exactamente uno por cada Bounded Context del equipo: `identidad_reputacion`, `catalogo`, `reservas` y `prestamos`."*

### Tabla de organización por integrante:
| Esquema (Schema) | Integrante / Responsable | Tablas principales | Propósito |
|---|---|---|---|
| `identidad_reputacion` | Persona 1 (Líder) | `usuario`, `perfil_reputacion`, `sancion`, `excepcion_academica` | Usuarios, credenciales, historial de sanciones y cálculo de reputación |
| `catalogo` | Persona 2 | `recurso`, `ficha_tecnica` | Inventario de recursos, categorización y especificaciones técnicas |
| `reservas` | Persona 3 | `reserva`, `turnos` | Solicitudes y asignación de franjas horarias prioritarias |
| `prestamos` | Persona 4 | `prestamo`, `devolucion`, `incidencia` | Ciclo de entrega física, seguimiento activo y recepción de recursos |

### ¿Cómo se crean los esquemas?
- En el archivo `db/init.sql`, ejecutado automáticamente al iniciar Docker por primera vez:
  ```sql
  CREATE SCHEMA IF NOT EXISTS identidad_reputacion;
  CREATE SCHEMA IF NOT EXISTS catalogo;
  CREATE SCHEMA IF NOT EXISTS reservas;
  CREATE SCHEMA IF NOT EXISTS prestamos;
  ```
- En los modelos de SQLAlchemy de cada módulo, se declara explícitamente el esquema:
  ```python
  __table_args__ = {"schema": "identidad_reputacion"}
  ```

> [!NOTE]
> **¿Por qué usamos esquemas separados?**
> Para garantizar el **aislamiento arquitectónico**: cada módulo tiene su propio espacio de nombres en la BD, evitando colisiones de nombres y simulando microservicios independientes sobre una misma base de datos relacional.

---

## 3. ¿Qué framework usan en el backend (Python) y cómo se ejecuta?

### Respuesta directa:
> *"Usamos **FastAPI** sobre **Python 3.11+**. Es un framework web moderno y de alto rendimiento basado en estándares abiertos (OpenAPI y JSON Schema). Se ejecuta con el servidor ASGI de alto rendimiento **Uvicorn**."*

### ¿Cómo se ejecuta el backend?
Existen dos formas principales:
1. **Comando directo con recarga en caliente (desarrollo):**
   ```bash
   cd backend
   .venv/bin/uvicorn prestamos_recursos.main:app --reload --app-dir src
   ```
2. **Mediante automatización:**
   ```bash
   ./dev.sh        # O también: make backend
   ```

### Características clave que justifican su elección:
- **Validación automática y tipado:** Utiliza **Pydantic v2** para validar requests y responses de forma estricta. Si un dato no cumple el tipo o formato, FastAPI rechaza la petición con código `422 Unprocessable Entity` antes de tocar el dominio.
- **Documentación interactiva automática:** Genera la documentación de la API en tiempo real en:
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`
- **Asincronía nativa y ASGI:** Preparado para alta concurrencia mediante `async/await` y servidores ASGI (`Uvicorn`).
- **Inyección de dependencias:** El sistema `Depends()` de FastAPI permite desacoplar la creación de sesiones de BD, autenticación y servicios.

---

## 4. ¿Qué framework usan en el frontend (JavaScript)?

### Respuesta directa:
> *"Usamos la librería **React 18** empaquetada y servida con la herramienta de construcción ultrarrápida **Vite**. La navegación entre vistas se gestiona mediante **React Router DOM**."*

### Características de la arquitectura frontend:
- **Estructura modular por feature:** En `frontend/src/features/` cada integrante tiene su carpeta correspondiente (ej. `identidad/`, `catalogo/`, `reservas/`, `prestamos/`), donde residen sus componentes, llamadas a API (`api.js`) y páginas (`pages/`).
- **Layout compartido:** Existe un layout principal (`frontend/src/layout/Layout.jsx`) con una barra de navegación dinámica que lee los roles del usuario desde el JWT almacenado en `localStorage`.
- **Diseño sin dependencias infladas:** Se utiliza CSS limpio con variables de diseño (Tokens de diseño en `tokens.css` y estilos base en `global.css`, esquema visual "Teal Campus").

### Comandos de ejecución:
```bash
cd frontend
npm run dev     # Inicia el servidor de desarrollo Vite en http://localhost:5173
npm run build   # Compila y optimiza para producción (valida sintaxis y bundling)
```

---

## 5. ¿Dónde viven los archivos HTML? ¿Existen los archivos HTML? (SPA)

### Respuesta directa:
> *"Nuestra aplicación web es una **Single Page Application (SPA)**. Por lo tanto, **sólo existe UN único archivo HTML real** en todo el proyecto: `frontend/index.html`. No existen páginas HTML separadas para el login, catálogo o reservas."*

### ¿Cómo funciona la SPA si solo hay un archivo HTML?
1. **El contenedor raíz:** `frontend/index.html` contiene únicamente la estructura básica con una etiqueta `<div>` vacía:
   ```html
   <!doctype html>
   <html lang="es">
     <head>
       <meta charset="UTF-8" />
       <title>Proyecto Interdisciplinar</title>
     </head>
     <body>
       <div id="root"></div>
       <script type="module" src="/src/main.jsx"></script>
     </body>
   </html>
   ```
2. **Montaje dinámico con React:**
   En `frontend/src/main.jsx`, React toma el control del elemento `#root`:
   ```javascript
   createRoot(document.getElementById("root")).render(
     <StrictMode>
       <App />
     </StrictMode>
   );
   ```
3. **¿Qué son entonces las pantallas (`LoginPage.jsx`, `CatalogoPage.jsx`, etc.)?**
   **No son HTML**, son componentes de **JSX** (JavaScript XML). React Router (`react-router-dom`) intercepta la URL en el navegador y monta o desmonta dinámicamente los componentes JSX en el DOM sin recargar la página.

> [!IMPORTANT]
> **Diferencia clave para explicar a la profesora:**
> - En una web tradicional multi-página (ej. PHP o Django clásico): cada clic hace una petición al servidor y este descarga un nuevo archivo `.html`.
> - En nuestra **SPA con React**: el servidor web entrega `index.html` y los paquetes JavaScript una sola vez. Cuando el usuario hace clic en «Catálogo», JavaScript cambia la vista al instante en el navegador del usuario y solo pide datos puros (JSON) al backend vía `fetch`.

---

## 6. ¿Qué arquitectura usan? (DDD + Clean Architecture)

### Respuesta directa:
> *"Implementamos **Domain-Driven Design (DDD)** combinado con **Arquitectura Limpia (Hexagonal / Clean Architecture)**. El sistema está dividido en **4 Bounded Contexts**, y cada uno de ellos contiene **4 capas estrictas** orientadas hacia el centro."*

### El flujo de dependencias:
```text
Presentation  ──>  Application  ──>  Domain  <──  Infrastructure
 (FastAPI / DTOs)     (Servicios Casos Uso)   (Entidades Puras)     (SQLAlchemy Repos)
```

### Detalle de las 4 capas:
1. **Dominio (`domain/`):**
   - **El corazón del sistema:** Contiene entidades, Value Objects, enums, excepciones de negocio y las interfaces abstractas de los repositorios (`Protocol` / `ABC`).
   - **Regla sagrada del dominio puro:** El dominio **NO importa nada externo**: ni FastAPI, ni SQLAlchemy, ni Pydantic, ni librerías de terceros. Es Python puro. Si cambiamos de framework web o de base de datos, el dominio no sufre ningún cambio.
2. **Aplicación (`application/`):**
   - Orquesta los casos de uso (ej. `RegistrarUsuarioService`, `AplicarSancionService`).
   - Define DTOs (Data Transfer Objects) para recibir y devolver datos planos.
   - Aplica validaciones de reglas de aplicación y transacciones.
3. **Infraestructura (`infrastructure/`):**
   - Implementa las interfaces del dominio con tecnologías concretas.
   - Contiene los modelos ORM de **SQLAlchemy** (`UsuarioModel`, `SancionModel`) y los repositorios SQL que ejecutan consultas en PostgreSQL.
4. **Presentación (`presentation/`):**
   - Routers y endpoints de **FastAPI** (`POST /usuarios`, `POST /auth/login`).
   - Traduce peticiones HTTP a llamadas de servicios de aplicación y serializa respuestas JSON con Pydantic.

---

## 7. ¿Cómo se comunican los 4 módulos de los 4 integrantes?

### Respuesta directa:
> *"Se comunican mediante **bajo acoplamiento (Loose Coupling)**. Ningún contexto puede importar directamente entidades de dominio ni modelos ORM de otro contexto. Entre ellos **sólo se intercambian identificadores primitivos (IDs como UUID o enteros)** o se interactúa a través de interfaces de servicios de aplicación."*

### Ejemplo concreto de la vida real del proyecto:
- Cuando el módulo de **`prestamos`** (Persona 4) necesita saber si un usuario puede pedir un equipo:
  - **INCORRECTO (prohibido):** `prestamos` importa `UsuarioModel` o `PerfilReputacionModel` de `identidad_reputacion` y consulta sus tablas. *(Esto rompería DDD y acoplaría los esquemas).*
  - **CORRECTO (lo implementado):** `prestamos` solo tiene el `usuario_id` (un UUID o entero) y consulta al servicio de aplicación o endpoint de identidad: `GET /reputacion/elegibilidad/{usuario_id}`.
- Cuando el módulo de **`reservas`** (Persona 3) aprueba una solicitud:
  - Solo pasa `reserva_id`, `usuario_id` y `recurso_id` primitivos.

```mermaid
flowchart LR
    subgraph Contexto Identidad
        IR_App[Servicio Reputación]
    end
    subgraph Contexto Préstamos
        P_App[Servicio Préstamos]
    end
    P_App -- "Consulta elegibilidad\nsolo con usuario_id (primitivo)" --> IR_App
```

> [!NOTE]
> Esta decisión nos permite trabajar a los 4 integrantes en paralelo en ramas separadas de Git (`feature/*`) sin pisarnos el código ni generar conflictos de merge en la base de datos.

---

## 8. ¿Quién hace el commit en la base de datos? (Unit of Work y Transacciones)

### Respuesta directa:
> *"El commit de la base de datos **lo realiza exclusivamente la dependencia compartida `shared.get_session`**, implementando el patrón **Unit of Work por petición HTTP (Decisión D13)**. Los repositorios y servicios de aplicación **NUNCA hacen `commit()`**, únicamente hacen `flush()` para obtener IDs autogenerados."*

### ¿Por qué se diseñó así? (Frontera de Transacción Atómica)
Si un repositorio hiciera `commit()` internamente y el proceso fallara en el siguiente paso (por ejemplo, validando una regla o enviando una respuesta 400), la base de datos quedaría en un **estado inconsistente con escrituras parciales**.

### El código que lo demuestra (`shared/database.py`):
```python
def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición.
    Frontera de transacción (unit of work, D13).
    """
    with SessionLocal() as session:
        try:
            yield session
            # Si la petición HTTP termina exitosamente (2xx):
            session.commit()
        except Exception:
            # Si ocurre cualquier error o excepción:
            session.rollback()
            raise
```

### Resumen del ciclo de vida de una transacción:
1. Llega la petición HTTP a FastAPI.
2. `get_session()` abre la sesión en la base de datos.
3. El servicio y el repositorio realizan cambios y usan `session.flush()` si necesitan que la BD asigne claves foráneas o IDs.
4. Si el endpoint responde correctamente: `get_session` ejecuta `session.commit()`.
5. Si ocurre cualquier error: `get_session` ejecuta `session.rollback()` y nada queda guardado.

---

## 9. ¿Cómo protegen contraseñas y sesiones? (Bcrypt + JWT)

### Respuesta directa:
> *"Las contraseñas se almacenan con hashing seguro mediante **Bcrypt con factor de costo 12**. Las sesiones se gestionan mediante **JSON Web Tokens (JWT)** con algoritmo **HS256**, firmados criptográficamente con una clave secreta (`JWT_SECRET`) y con un tiempo de vida (expiración) de **24 horas**."*

### Componentes de seguridad:

| Aspecto | Tecnología / Parámetro | Detalle de Implementación |
|---|---|---|
| **Hash de Contraseñas** | Bcrypt (`cost=12`) | La contraseña en texto plano jamás se guarda ni viaja en logs. Se usa salting automático. El costo 12 equilibra seguridad contra ataques de fuerza bruta y tiempo de cómputo en el servidor. |
| **Tokens de Sesión** | PyJWT (`alg=HS256`) | El token contiene en su *payload* los claims: `sub` (ID del usuario), `roles` (lista de roles asignados) y `exp` (timestamp de expiración en 24h). |
| **Firma Criptográfica** | Clave simétrica `JWT_SECRET` | Es una variable de entorno obligatoria. Si falta, la aplicación ni siquiera arranca. |
| **Envío y Validación** | Cabecera `Authorization: Bearer <token>` | El cliente React almacena el token en `localStorage` y el cliente HTTP (`apiClient.js`) lo adjunta en cada petición protegida. |
| **Control de Acceso (RBAC)** | Dependencia `require_roles(...)` | Endpoints como `/usuarios` verifican que el token incluya roles específicos como `ADMINISTRADOR_SISTEMA`. Si no, responde `403 Forbidden`. |
| **Protección anti fuerza bruta** | Rate Limiting con **Slowapi** | Endpoints críticos como `/auth/login` limitan el número de intentos por IP para evitar ataques automatizados. |

> [!TIP]
> **Diferencia entre 401 y 403:**
> - **401 Unauthorized:** *«No sé quién eres»* (no enviaste token o ya expiró).
> - **403 Forbidden:** *«Sé quién eres, pero tu rol no tiene permiso para entrar aquí»* (ej. un estudiante queriendo borrar usuarios).

---

## 10. ¿Cómo prueban el sistema y aseguran la calidad? (Pytest + Ruff)

### Respuesta directa:
> *"Aseguramos la calidad mediante una pirámide de pruebas automatizadas con **Pytest**, dividida en tres niveles con marcadores (`unit`, `integration`, `e2e`), y mediante análisis estático y formateo de código con **Ruff**."*

### 1. La pirámide de pruebas (Pytest):
- **Pruebas Unitarias (`-m unit`):** Prueban la lógica de negocio pura en `domain/` y `application/`. No tocan la base de datos ni Docker; usan dobles de prueba (mocks o repositorios en memoria). Se ejecutan en segundos.
- **Pruebas de Integración (`-m integration`):** Prueban los repositorios SQLAlchemy contra la base de datos real en Docker (`prestamos_db`). Verifican que las consultas SQL, tipos ENUM y esquemas funcionen correctamente.
- **Pruebas de Extremo a Extremo (`-m e2e`):** Prueban la API completa de punta a punta usando el `TestClient` de FastAPI (desde la petición HTTP, pasando por autenticación JWT, hasta la persistencia en base de datos).

```bash
# Cómo correr las pruebas desde la terminal:
cd backend
.venv/bin/pytest                     # Corre todas las pruebas
.venv/bin/pytest -m unit             # Solo pruebas unitarias (rápidas)
.venv/bin/pytest -m integration      # Pruebas con BD PostgreSQL
.venv/bin/pytest -m e2e              # Pruebas integrales de endpoints
```

### 2. Linteo y estilo (Ruff):
- Usamos **Ruff**, el linter y formateador ultrarrápido para Python.
- Configurado con longitud máxima de línea de **100 caracteres** y reglas de buenas prácticas.
- Comando:
  ```bash
  cd backend && .venv/bin/ruff check src
  ```

### 3. Verificación de Frontend:
- Ejecutamos `npm run build` en `frontend/` para asegurar que no existan errores de sintaxis JSX, problemas de imports o referencias no resueltas.

---

## 11. Chuleta rápida: «Para responder en 10 segundos»

Usa esta tabla para un repaso de último minuto antes de entrar a la evaluación:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CHULETA DE SUPERVIVENCIA - DEFENSA TI2                          │
├────────────────────────────┬───────────────────────────────────────────────────────────┤
│ Pregunta de la Profesora   │ Tu respuesta clave                                        │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Base de datos y motor      │ PostgreSQL 16 en contenedor Docker prestamos_db.          │
│                            │ BD: prestamos_recursos. Usuario: prestamos.               │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Organización de tablas     │ 4 esquemas (schemas): identidad_reputacion, catalogo,     │
│                            │ reservas y prestamos (uno por integrante).                │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Backend y ejecución        │ FastAPI + Python 3.11+. Se ejecuta con Uvicorn (ASGI).    │
│                            │ Validación estricta con Pydantic v2.                      │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Frontend                   │ React 18 con Vite y React Router DOM.                     │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Archivos HTML en frontend  │ ¡Solo existe UNO! (index.html con <div id="root"></div>). │
│                            │ Es una SPA; las páginas son componentes JSX dinámicos.    │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Arquitectura               │ Domain-Driven Design (DDD) + Arquitectura Limpia en       │
│                            │ 4 capas: Presentation, Application, Domain, Infra.        │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Dominio Puro               │ El dominio NO depende de frameworks (cero SQLAlchemy,     │
│                            │ cero FastAPI, cero Pydantic). Es lógica pura en Python.   │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Comunicación entre módulos │ Bajo acoplamiento: solo IDs primitivos y servicios de     │
│                            │ aplicación. Prohibido importar entidades de otro módulo.  │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ ¿Quién hace el commit?     │ shared.get_session (Unit of Work por petición HTTP).      │
│                            │ Los repositorios y servicios SOLO hacen flush.            │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Contraseñas y sesiones     │ Bcrypt (costo 12) + JWT HS256 (24 horas de vigencia).     │
│                            │ Autorización por roles (RBAC) y Rate Limit con Slowapi.   │
├────────────────────────────┼───────────────────────────────────────────────────────────┤
│ Pruebas y calidad          │ Pytest (unit, integration, e2e) y linter Ruff.            │
│                            │ Compilación con Vite (npm run build).                     │
└────────────────────────────┴───────────────────────────────────────────────────────────┘
```
