# Proyecto Interdisciplinar

Sistema de Gestión de Préstamos de Recursos.
Stack: **Python (FastAPI + SQLAlchemy) · React (Vite) · PostgreSQL**.
Arquitectura: **DDD por bounded context**, con las capas del diagrama
(`domain`, `application`, `infrastructure`, `presentation`) dentro de cada contexto.

## Estructura

```
backend/src/prestamos_recursos/
├── main.py, config.py
├── shared/                      # base_entity.py, database.py
└── contexts/
    ├── identidad_reputacion/    # Usuario, PerfilReputacion, Sancion, ExcepcionAcademica
    ├── catalogo/                # Recurso, FichaTecnica
    ├── reservas/                # Reserva, AlgoritmoPrioridadService
    └── prestamos/               # Prestamo, Checklist, Garantia
frontend/src/features/           # una carpeta por contexto: identidad, catalogo, reservas, prestamos
db/init.sql                      # schemas de PostgreSQL (uno por contexto)
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

## Cómo levantar el proyecto

```bash
# 1. Variables de entorno
cp .env.example .env

# 2. Base de datos
docker compose up -d

# 3. Backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn prestamos_recursos.main:app --reload --app-dir src
pytest

# 4. Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

Backend: http://localhost:8000/docs · Frontend: http://localhost:5173
