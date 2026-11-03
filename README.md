# Proyecto Interdisciplinar — Préstamos de Recursos

Sistema de Gestión de Préstamos de Recursos.
Stack: **Python (FastAPI + SQLAlchemy) · React (Vite) · PostgreSQL 16**.
Arquitectura: **DDD por bounded context**, con las capas del diagrama (`domain`, `application`, `infrastructure`, `presentation`) dentro de cada contexto y un schema de PostgreSQL por contexto.

## Estructura

```
backend/src/prestamos_recursos/
├── main.py, config.py
├── shared/                      # base_entity.py, database.py, rate_limit.py
└── contexts/
    ├── identidad_reputacion/    # Usuario, PerfilReputacion, Sancion, ExcepcionAcademica
    ├── catalogo/                # Recurso, FichaTecnica
    ├── reservas/                # Reserva, AlgoritmoPrioridadService
    └── prestamos/               # Prestamo, Checklist, Garantia
frontend/src/features/           # una carpeta por contexto: identidad, catalogo, reservas, prestamos
db/init.sql                      # schemas de PostgreSQL (uno por contexto)
db/seed.sql                      # datos iniciales (usuarios de prueba y recursos del catálogo)
scripts/consultar.sh             # utilidad para consultas SQL en la base de datos local
dev.sh                           # script para levantar BD, backend, seed y frontend juntos
```

## Reparto del equipo

| Persona | Contexto (backend) | Feature (frontend) |
|---|---|---|
| 1 | `identidad_reputacion` | `identidad` |
| 2 | `catalogo` | `catalogo` |
| 3 | `reservas` | `reservas` |
| 4 | `prestamos` | `prestamos` |

## Reglas del equipo

1. Cada persona trabaja solo dentro de su contexto (`contexts/<contexto>/` y `features/<feature>/`).
2. Un agregado referencia a otro **solo por ID** (`usuario_id`, `recurso_id`), nunca importa sus clases.
3. Si un contexto necesita algo de otro, lo hace a través del servicio de `application/` del otro contexto.
4. Nadie hace push directo a `main`: rama `feature/<nombre>` + Pull Request.
5. Los archivos compartidos (`shared/`, `main.py`, `docker-compose.yml`, `db/`) se avisan antes de tocarlos.

## Instalación inicial (primera vez)

```bash
# 1. Variables de entorno
cp .env.example .env

# 2. Dependencias del backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..

# 3. Dependencias del frontend
cd frontend
npm install
cd ..
```

## Cómo levantar el proyecto

Para levantar la base de datos, el backend y el frontend al mismo tiempo, ejecuta desde la raíz:

```bash
./dev.sh
```

El script inicia PostgreSQL en Docker, arranca FastAPI (creando las tablas automáticamente), carga los datos de prueba de `db/seed.sql` y levanta Vite. Con `Ctrl+C` se detienen todos los servicios.

Si prefieres levantar cada parte por separado:

```bash
# Base de datos
docker compose up -d

# Backend
cd backend && .venv/bin/uvicorn prestamos_recursos.main:app --reload --app-dir src

# Frontend (en otra terminal)
cd frontend && npm run dev
```

Backend (Swagger): http://localhost:8000/docs · Frontend: http://localhost:5173

## Datos de prueba precargados (`db/seed.sql`)

Al iniciar con `./dev.sh` se cargan 8 recursos en el catálogo (equipos de cómputo, multimedia, laboratorio y libros) y dos cuentas listas para probar los flujos según el rol:

| Rol | Correo | Contraseña | Permisos principales |
|---|---|---|---|
| Administrador / Gestor | `admin@example.com` | `admin123` | Registrar recursos y cambiar su estado, ver todas las reservas y préstamos, confirmar reservas, iniciar préstamos, registrar entregas con garantía/checklist, procesar devoluciones y gestionar reputación/sanciones. |
| Estudiante | `estudiante@example.com` | `estudiante123` | Consultar el catálogo, solicitar reservas (o entrar a la cola de espera priorizada por reputación), ver sus préstamos y checklists, y renovar préstamos activos (+7 días). |

Si necesitas recargar manualmente estos datos en cualquier momento:

```bash
docker compose exec -T db psql -U prestamos -d prestamos_recursos < db/seed.sql
```

## Consultas SQL de desarrollo (`scripts/consultar.sh`)

Para inspeccionar las tablas de PostgreSQL sin configurar credenciales manualmente:

```bash
# Ejecutar una consulta directa
./scripts/consultar.sh 'SELECT id, nombre, correo, roles FROM identidad_reputacion.usuario;'
./scripts/consultar.sh 'SELECT nombre, categoria, estado FROM catalogo.recursos;'
./scripts/consultar.sh 'SELECT id, usuario_id, recurso_id, estado FROM reservas.reservas;'
./scripts/consultar.sh 'SELECT id, usuario_id, recurso_id, estado FROM prestamos.prestamos;'

# O abrir la consola interactiva psql (con search_path configurado en los 4 schemas)
./scripts/consultar.sh
```

## Tests y linter

Con el contenedor de PostgreSQL corriendo (`docker compose up -d`):

```bash
cd backend
.venv/bin/pytest           # suite completa (unit, integration, e2e)
.venv/bin/pytest -m unit   # solo tests unitarios
.venv/bin/ruff check src   # linter
```
