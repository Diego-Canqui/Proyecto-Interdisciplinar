# Reservas

El módulo permite crear, consultar, listar por usuario, confirmar y cancelar
reservas, además de consultar la cola de un recurso. La API usa PostgreSQL y crea
la tabla de Reservas al iniciar. Las reservas se conservan después de reiniciar
el backend.

## Iniciar el backend

Desde la raíz del repositorio:

```bash
cp .env.example .env
docker compose up -d
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn prestamos_recursos.main:app --reload --app-dir src
```

En Windows, activar el entorno con `.venv\Scripts\activate`. Abrir
`http://localhost:8000/docs` y buscar Reservas.

## Operaciones

- `POST /reservas`: crear con `usuario_id`, `recurso_id`, `fecha_inicio` y `fecha_fin`.
- `GET /reservas/{id_reserva}`: consultar por el ID devuelto al crear.
- `GET /reservas/usuario/{id_usuario}`: listar por usuario.
- `PATCH /reservas/{id_reserva}/confirmar`: confirmar una reserva pendiente vigente.
- `PATCH /reservas/{id_reserva}/cancelar`: cancelar una reserva.
- `GET /reservas/recurso/{id_recurso}/cola`: consultar la cola de espera.

Los IDs deben ser UUID y la fecha final debe ser posterior a la inicial. Se
rechazan cruces con reservas pendientes o confirmadas del mismo recurso; los
horarios consecutivos se permiten. Confirmar una reserva vencida o en un estado
distinto de pendiente no está permitido. La API devuelve 404 si no existe,
409 para conflictos de horario o de estado, y 422 si los datos son inválidos.

## Pruebas

Las pruebas usan SQLite en memoria y no requieren Docker. Desde `backend`:

```bash
source .venv/bin/activate
DATABASE_URL=sqlite+pysqlite:///:memory: python -m pytest tests src/prestamos_recursos/contexts/reservas/tests
```

La ruta del contexto se indica porque pytest busca por defecto en `backend/tests`.

## Pendiente

Autenticación y autorización, validar usuario y recurso con los otros contextos,
reglas definitivas de prioridad e integrar la conversión a préstamo. La cola
actual usa fecha de inicio como orden provisional.
