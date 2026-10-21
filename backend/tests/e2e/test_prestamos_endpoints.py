from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.presentation.dependencies import get_prestamo_service
from prestamos_recursos.main import app

client = TestClient(app)


class FakePrestamoRepository:
    def __init__(self, prestamos: list[Prestamo] | None = None) -> None:
        self.prestamos = prestamos or []

    def obtener_por_usuario(self, id_usuario):
        return [p for p in self.prestamos if p.usuario_id == id_usuario]


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.e2e
def test_consultar_historial_usuario_sin_prestamos():
    usuario_id = uuid4()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    response = client.get(f"/prestamos/usuarios/{usuario_id}/historial")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.e2e
def test_consultar_historial_con_prestamos():
    usuario_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 20, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 25, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

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

