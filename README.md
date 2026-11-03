# Sistema de Gestión de Préstamos de Recursos

Aplicación web full-stack para gestionar el catálogo de equipos/libros institucionales, reservas con lista de espera priorizada por reputación dinámica, préstamos en ventanilla con garantía y checklist de inspección física (salida/retorno), y control de sanciones.

- **Stack:** Python 3.11+ (FastAPI, SQLAlchemy 2.0, Pydantic v2, PyJWT, slowapi) · React 18 (Vite) · PostgreSQL 16 (Docker).
- **Arquitectura:** **Domain-Driven Design (DDD)** dividido en **4 Bounded Contexts** independientes, cada uno con sus 4 capas (`domain`, `application`, `infrastructure`, `presentation`) y su propio schema en PostgreSQL.

---

## 👥 Equipo y Bounded Contexts

| Integrante | Contexto (Backend) | Feature (Frontend) | Responsabilidad principal |
|---|---|---|---|
| **1** | `identidad_reputacion` | `identidad` | Autenticación JWT, roles, reputación dinámica (0–1000 pts), sanciones y excepciones académicas. |
| **2** | `catalogo` | `catalogo` | Gestión de recursos, fichas técnicas (marca, modelo, serie, estado físico) y disponibilidad. |
| **3** | `reservas` | `reservas` | Solicitud de reservas, confirmación automática/manual y cola de espera ordenada por reputación. |
| **4** | `prestamos` | `prestamos` | Conversión a préstamo, entrega física con garantía + checklist, devolución con detección de daños y renovación (+7 días). |

---

## 🛠️ Instalación por primera vez (solo se hace una vez)

1. **Configurar variables de entorno:**
   Copia el archivo de ejemplo en la raíz del proyecto:
   ```bash
   cp .env.example .env
   ```

2. **Instalar dependencias del Backend (Python):**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   cd ..
   ```

3. **Instalar dependencias del Frontend (Node.js):**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

---

## 🚀 Cómo prender todo el proyecto (con un solo comando)

Desde la raíz del proyecto, ejecuta el script de desarrollo:

```bash
./dev.sh
```

### ¿Qué hace `./dev.sh` automáticamente por ti?
1. 🐘 Levanta el contenedor de **PostgreSQL 16** en Docker (`docker compose up -d`).
2. 🐍 Inicia el **Backend (FastAPI)** en `http://localhost:8000` y crea las tablas de los 4 schemas si aún no existen.
3. 🌱 Carga automáticamente los **datos iniciales ([`db/seed.sql`](db/seed.sql))**: crea los usuarios de prueba y **8 recursos** (Laptop Dell, Proyector Epson 4K, Kit de Electrónica/Arduino y 5 libros clásicos) para que el catálogo nunca aparezca vacío.
4. ⚛️ Inicia el **Frontend (React + Vite)** en `http://localhost:5173`.
5. 🛑 Cuando presionas **`Ctrl + C`**, apaga el frontend, el backend y el contenedor de Docker limpiamente.

### 🌐 Enlaces rápidos una vez encendido
- **Aplicación Web (Frontend):** [http://localhost:5173](http://localhost:5173)
- **Documentación interactiva API (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 👤 Cuentas precargadas para probar el sistema

Al levantar el servidor con `./dev.sh` (o cargando `db/seed.sql`), ya tienes listas estas dos cuentas:

| Rol | Correo | Contraseña | Qué puedes probar con esta cuenta |
|---|---|---|---|
| **Administrador / Gestor de Almacén** | `admin@example.com` | `admin123` | Registrar nuevos recursos, cambiar estado operativo, ver reservas/préstamos de todos los usuarios, confirmar reservas, iniciar préstamos, realizar entrega física con checklist/garantía, registrar devoluciones (con o sin daños) y gestionar reputación/sanciones. |
| **Estudiante** | `estudiante@example.com` | `estudiante123` | Explorar el catálogo y sus fichas técnicas, solicitar reservas (o entrar en lista de espera si el horario está ocupado), consultar sus préstamos, ver el checklist de sus equipos y renovar préstamos (+7 días). |

---

## 🗄️ Cómo consultar la Base de Datos SQL (`consultar.sh`)

El proyecto incluye el script [`scripts/consultar.sh`](scripts/consultar.sh) para que puedas inspeccionar las tablas de PostgreSQL sin tener que escribir contraseñas ni configurar conexiones:

### Opción A: Ejecutar una consulta SQL rápida desde la terminal
Pásale la consulta entre comillas:
```bash
# Ver todos los usuarios registrados
./scripts/consultar.sh 'SELECT id, nombre, correo, roles FROM identidad_reputacion.usuario;'

# Ver los recursos del catálogo y su estado actual
./scripts/consultar.sh 'SELECT nombre, categoria, numero_serie, estado FROM catalogo.recursos;'

# Ver las reservas activas o en cola
./scripts/consultar.sh 'SELECT id, usuario_id, recurso_id, estado, fecha_inicio, fecha_fin FROM reservas.reservas;'

# Ver los préstamos registrados
./scripts/consultar.sh 'SELECT id, usuario_id, recurso_id, estado, fecha_inicio, fecha_fin FROM prestamos.prestamos;'
```

### Opción B: Entrar a la consola interactiva de PostgreSQL (`psql`)
Ejecútalo sin argumentos:
```bash
./scripts/consultar.sh
```
Dentro de la consola interactiva puedes usar:
- `\dn` → listar los 4 schemas (`identidad_reputacion`, `catalogo`, `reservas`, `prestamos`).
- `\dt catalogo.*` → ver las tablas de un schema específico.
- `\q` → salir de la consola.

### Opción C: Recargar manualmente los datos semilla (`db/seed.sql`)
Si borraste recursos o quieres restaurar los 8 recursos y las 2 cuentas por defecto en cualquier momento:
```bash
docker compose exec -T db psql -U prestamos -d prestamos_recursos < db/seed.sql
```

---

## 🧪 Cómo ejecutar los Tests y el Linter

Con la base de datos arriba (`docker compose up -d`), ejecuta desde la carpeta `backend`:

```bash
cd backend

# Ejecutar toda la suite de pruebas (Unitarios + Integración + E2E = 392 tests)
.venv/bin/pytest

# Ejecutar solo un tipo de test
.venv/bin/pytest -m unit
.venv/bin/pytest -m integration
.venv/bin/pytest -m e2e

# Ejecutar el linter (Ruff)
.venv/bin/ruff check src
```

---

## 📂 Estructura del Proyecto

```text
Proyecto-Interdisciplinar/
├── dev.sh                           # Script principal: levanta BD, Backend, Seed y Frontend
├── docker-compose.yml               # Contenedor PostgreSQL 16
├── db/
│   ├── init.sql                     # Crea los 4 schemas de PostgreSQL al inicializar el contenedor
│   └── seed.sql                     # Datos semilla: usuarios de prueba y 8 recursos del catálogo
├── scripts/
│   └── consultar.sh                 # Utilidad para ejecutar consultas SQL o abrir psql interactivo
├── backend/
│   ├── pyproject.toml               # Dependencias de Python y configuración de pytest/ruff
│   ├── src/prestamos_recursos/
│   │   ├── main.py                  # Punto de entrada FastAPI (routers, CORS, rate limit)
│   │   ├── config.py                # Variables de entorno (Pydantic Settings)
│   │   ├── shared/                  # BaseEntity, sesión de BD (get_session) y rate limiter
│   │   └── contexts/                # Los 4 Bounded Contexts (DDD)
│   │       ├── identidad_reputacion/
│   │       ├── catalogo/
│   │       ├── reservas/
│   │       └── prestamos/
│   └── tests/                       # Suite de pruebas (unit/, integration/, e2e/)
└── frontend/
    ├── package.json
    └── src/
        ├── App.jsx                  # Rutas de la aplicación
        ├── components/Layout.jsx    # Barra de navegación adaptada según el rol del JWT
        ├── lib/apiClient.js         # Cliente HTTP (GET, POST, PUT, PATCH) con inyección de Bearer token
        └── features/                # Módulos de interfaz por cada Bounded Context
            ├── identidad/           # Login, Registro y Gestión de Reputación/Sanciones
            ├── catalogo/            # Catálogo, Ficha Técnica, Registro de Recursos y Cambio de Estado
            ├── reservas/            # Mis Reservas, Solicitud y Cola de Espera por Reputación
            └── prestamos/           # Ventanilla de Entrega (Garantía + Checklist), Devolución y Renovación
```
