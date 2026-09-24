# Avance de reservas

El módulo permite crear, consultar y cancelar reservas, y consultar la cola de un
recurso. Usa almacenamiento en memoria: los datos se pierden al reiniciar y no se
comparten entre procesos. La cola incluye reservas pendientes que no han vencido,
ordenadas provisionalmente por fecha de inicio.

## Probar la API

Desde `backend`, con las dependencias del proyecto instaladas:

```bash
uvicorn prestamos_recursos.main:app --reload --app-dir src
```

Abrir `http://localhost:8000/docs` y buscar la sección Reservas:

- `POST /reservas`: crear con `usuario_id`, `recurso_id`, `fecha_inicio` y `fecha_fin`.
- `GET /reservas/{id_reserva}`: consultar por el ID devuelto al crear.
- `PATCH /reservas/{id_reserva}/cancelar`: cancelar una reserva.
- `GET /reservas/recurso/{id_recurso}/cola`: consultar la cola de espera.

Los IDs deben ser UUID y las fechas deben tener un rango válido. Para probar la
cola, usar fechas futuras con zona horaria, por ejemplo el sufijo `Z` para UTC.
La API responde con 404 si no existe la reserva, 409 si no puede cancelarse en su
estado actual y 422 si los datos enviados son inválidos.

## Pruebas

Desde `backend`:

```bash
pytest tests src/prestamos_recursos/contexts/reservas/tests
```

La ruta del contexto se indica explícitamente porque la configuración general de
pytest solo busca por defecto en `backend/tests`.

## Pendiente

Persistencia en PostgreSQL, autenticación y autorización, validación de usuarios
y recursos con los otros módulos, reglas definitivas de prioridad y conversión
a préstamo. Esta entrega es un avance funcional, no el módulo terminado.
