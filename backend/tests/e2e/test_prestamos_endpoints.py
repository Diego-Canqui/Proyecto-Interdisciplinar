from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_prestamo_repository import (
    SqlPrestamoRepository,
)
from prestamos_recursos.main import app

client = TestClient(app)


@pytest.mark.e2e
def test_consultar_historial_usuario_sin_prestamos(db_session):
    usuario_id = uuid4()
    response = client.get(f"/prestamos/usuarios/{usuario_id}/historial")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.e2e
def test_consultar_historial_con_prestamos(db_session):
    usuario_id = uuid4()
    repo = SqlPrestamoRepository(db_session)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 20, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 25, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    repo.guardar(prestamo)
    db_session.commit()

    response = client.get(f"/prestamos/usuarios/{usuario_id}/historial")
    assert response.status_code == 200
    datos = response.json()
    assert len(datos) == 1
    assert datos[0]["id"] == str(prestamo.id)
    assert datos[0]["usuario_id"] == str(usuario_id)
    assert datos[0]["estado"] == "ACTIVO"


@pytest.mark.e2e
def test_registrar_devolucion_retorna_501_pendiente():
    prestamo_id = uuid4()
    response = client.post(f"/prestamos/{prestamo_id}/devolucion")
    assert response.status_code == 501
    assert response.json()["detail"] == "Pendiente de implementar"

