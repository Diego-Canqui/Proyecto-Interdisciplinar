# Reservas

El módulo permite crear, consultar, listar por usuario, confirmar y cancelar
reservas, consultar la cola y convertir una reserva confirmada en préstamo.
Rechaza horarios que se cruzan para el mismo recurso.

## Iniciar el proyecto

El backend requiere PostgreSQL. Desde la raíz del repositorio, crea la
configuración local y levanta la base de datos:

```bash
cp .env.example .env
docker compose up -d
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn prestamos_recursos.main:app --reload --app-dir src
```

En otra terminal inicia el frontend:

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173/login`. Para probar inicio de sesión primero crea una
cuenta en `http://localhost:5173/registro`. La documentación de la API está en
`http://localhost:8000/docs`. El archivo `.env` debe incluir `JWT_SECRET`; la
plantilla ya proporciona una clave local de desarrollo.

## Operaciones de reservas

- `POST /reservas`: crear con `usuario_id`, `recurso_id`, `fecha_inicio` y `fecha_fin`.
- `GET /reservas/{id_reserva}`: consultar por ID.
- `GET /reservas/usuario/{id_usuario}`: listar por usuario.
- `PATCH /reservas/{id_reserva}/confirmar`: confirmar una reserva pendiente vigente.
- `PATCH /reservas/{id_reserva}/cancelar`: cancelar una reserva.
- `GET /reservas/recurso/{id_recurso}/cola`: consultar la cola.

Los IDs deben ser UUID y la fecha final posterior a la inicial. Horarios
consecutivos se permiten; solapamientos devuelven HTTP 409. Datos inválidos
devuelven HTTP 422 y reservas inexistentes HTTP 404.

## Pruebas

Con PostgreSQL arriba y desde `backend`, con el entorno virtual activo:

```bash
python -m pytest -q
```
