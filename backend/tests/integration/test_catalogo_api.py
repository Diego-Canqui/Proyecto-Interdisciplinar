from prestamos_recursos.contexts.catalogo.infrastructure.models.recurso_model import RecursoModel
from prestamos_recursos.shared.database import Base, engine
from fastapi.testclient import TestClient
from prestamos_recursos.main import app
import pytest

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_crear_y_buscar_recurso():
    response = client.post(
        "/recursos",
        json={
            "nombre": "Proyector Epson",
            "descripcion": "Proyector HD",
            "categoria": "Multimedia",
            "marca": "Epson",
            "modelo": "PowerLite",
            "numero_serie": "EPSON999",
            "color": "Blanco",
            "estado_fisico": "Nuevo",
            "foto_url": "http://example.com/proyector.jpg"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data

    recurso_id = data["id"]

    # Buscar recursos
    res_buscar = client.get("/recursos")
    assert res_buscar.status_code == 200
    recursos = res_buscar.json()
    assert len(recursos) == 1
    assert recursos[0]["nombre"] == "Proyector Epson"

    # Consultar disponibilidad
    res_disp = client.get(f"/recursos/{recurso_id}/disponibilidad")
    assert res_disp.status_code == 200
    assert res_disp.json()["disponible"] is True

    # Obtener ficha técnica
    res_ficha = client.get(f"/recursos/{recurso_id}/ficha-tecnica")
    assert res_ficha.status_code == 200
    ficha_data = res_ficha.json()
    assert ficha_data["marca"] == "Epson"
    assert ficha_data["numero_serie"] == "EPSON999"
