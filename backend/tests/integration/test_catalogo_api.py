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

    # Actualizar datos del recurso
    res_act = client.put(
        f"/recursos/{recurso_id}",
        json={
            "nombre": "Proyector Epson Pro",
            "descripcion": "Proyector HD 4K",
            "categoria": "Multimedia",
            "marca": "Epson",
            "modelo": "PowerLite 4K",
            "numero_serie": "EPSON999",
            "color": "Negro",
            "estado_fisico": "Excelente",
            "foto_url": "http://example.com/proyector2.jpg",
        },
    )
    assert res_act.status_code == 200
    assert res_act.json()["nombre"] == "Proyector Epson Pro"

    # Actualizar estado a MANTENIMIENTO
    res_est = client.patch(
        f"/recursos/{recurso_id}/estado",
        json={"estado": "MANTENIMIENTO"},
    )
    assert res_est.status_code == 200
    assert res_est.json()["estado"] == "MANTENIMIENTO"

    # Consultar disponibilidad ahora debe ser False
    res_disp2 = client.get(f"/recursos/{recurso_id}/disponibilidad")
    assert res_disp2.status_code == 200
    assert res_disp2.json()["disponible"] is False
