from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from prestamos_recursos.contexts.catalogo.infrastructure.models.recurso_model import RecursoModel  # noqa: F401
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import UsuarioDTO
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    get_current_user,
)
from prestamos_recursos.main import app
from prestamos_recursos.shared.database import Base, engine

client = TestClient(app)


def _crear_usuario_mock(rol: RolUsuario) -> UsuarioDTO:
    return UsuarioDTO(
        id=uuid4(),
        nombre="Usuario Prueba",
        correo="prueba@universidad.edu",
        telefono=None,
        roles=[rol],
        estado=True,
    )


def _payload_recurso(numero_serie: str = "EPSON999") -> dict:
    return {
        "nombre": "Proyector Epson",
        "descripcion": "Proyector HD",
        "categoria": "Multimedia",
        "marca": "Epson",
        "modelo": "PowerLite",
        "numero_serie": numero_serie,
        "color": "Blanco",
        "estado_fisico": "Nuevo",
        "foto_url": "http://example.com/proyector.jpg",
    }


@pytest.fixture(autouse=True)
def setup_database():
    app.dependency_overrides.clear()
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_crear_y_buscar_recurso():
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario_mock(
        RolUsuario.GESTOR_ALMACEN
    )
    response = client.post("/recursos", json=_payload_recurso())
    assert response.status_code == 201
    data = response.json()
    assert "id" in data

    recurso_id = data["id"]

    # Buscar recursos (sin sesión también accesible)
    app.dependency_overrides.clear()
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

    # Actualizar datos del recurso (con rol de gestión)
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario_mock(
        RolUsuario.ADMINISTRADOR_SISTEMA
    )
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


def test_escritura_catalogo_sin_autenticacion_retorna_401():
    recurso_id = uuid4()

    res_post = client.post("/recursos", json=_payload_recurso("SERIE-401"))
    assert res_post.status_code == 401

    res_put = client.put(f"/recursos/{recurso_id}", json=_payload_recurso("SERIE-401"))
    assert res_put.status_code == 401

    res_patch = client.patch(f"/recursos/{recurso_id}/estado", json={"estado": "MANTENIMIENTO"})
    assert res_patch.status_code == 401


def test_escritura_catalogo_con_estudiante_retorna_403():
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario_mock(
        RolUsuario.GESTOR_ALMACEN
    )
    creado = client.post("/recursos", json=_payload_recurso("SERIE-403"))
    assert creado.status_code == 201
    recurso_id = creado.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: _crear_usuario_mock(RolUsuario.ESTUDIANTE)

    res_post = client.post("/recursos", json=_payload_recurso("SERIE-403-2"))
    assert res_post.status_code == 403

    res_put = client.put(f"/recursos/{recurso_id}", json=_payload_recurso("SERIE-403"))
    assert res_put.status_code == 403

    res_patch = client.patch(f"/recursos/{recurso_id}/estado", json={"estado": "MANTENIMIENTO"})
    assert res_patch.status_code == 403


def test_crear_dos_libros_sin_numero_serie_ni_campos_opcionales():
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario_mock(
        RolUsuario.GESTOR_ALMACEN
    )

    libro_1 = {
        "nombre": "Clean Code",
        "descripcion": "Libro de ingeniería de software",
        "categoria": "Libros",
        "estado_fisico": "Nuevo",
        "foto_url": "http://example.com/cleancode.jpg",
        "especificaciones": {"autor": "Robert C. Martin", "isbn": "978-0132350884"},
    }
    libro_2 = {
        "nombre": "Design Patterns",
        "descripcion": "Patrones de diseño",
        "categoria": "Libros",
        "marca": "",
        "modelo": "   ",
        "numero_serie": "   ",
        "color": "",
        "estado_fisico": "Bueno",
        "foto_url": "http://example.com/gof.jpg",
    }

    res_1 = client.post("/recursos", json=libro_1)
    assert res_1.status_code == 201
    id_1 = res_1.json()["id"]

    res_2 = client.post("/recursos", json=libro_2)
    assert res_2.status_code == 201
    id_2 = res_2.json()["id"]

    res_ficha_1 = client.get(f"/recursos/{id_1}/ficha-tecnica")
    assert res_ficha_1.status_code == 200
    ficha_1 = res_ficha_1.json()
    assert ficha_1["marca"] is None
    assert ficha_1["modelo"] is None
    assert ficha_1["numero_serie"] is None
    assert ficha_1["color"] is None
    assert ficha_1["especificaciones"] == {
        "autor": "Robert C. Martin",
        "isbn": "978-0132350884",
    }

    res_ficha_2 = client.get(f"/recursos/{id_2}/ficha-tecnica")
    assert res_ficha_2.status_code == 200
    ficha_2 = res_ficha_2.json()
    assert ficha_2["marca"] is None
    assert ficha_2["modelo"] is None
    assert ficha_2["numero_serie"] is None
    assert ficha_2["color"] is None
    assert ficha_2["especificaciones"] == {}


def test_actualizar_recurso_con_especificaciones_json():
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario_mock(
        RolUsuario.GESTOR_ALMACEN
    )
    res_crear = client.post("/recursos", json=_payload_recurso("SERIE-SPEC-1"))
    assert res_crear.status_code == 201
    recurso_id = res_crear.json()["id"]

    # Verificar default {} en recurso creado sin especificaciones
    res_get = client.get(f"/recursos/{recurso_id}/ficha-tecnica")
    assert res_get.status_code == 200
    assert res_get.json()["especificaciones"] == {}

    # Actualizar agregando especificaciones y limpiando numero_serie con espacios
    res_put = client.put(
        f"/recursos/{recurso_id}",
        json={
            "nombre": "Proyector Epson Actualizado",
            "descripcion": "Proyector HD",
            "categoria": "Audio y Video",
            "marca": "Epson",
            "modelo": "PowerLite",
            "numero_serie": "   ",
            "color": "",
            "estado_fisico": "Bueno",
            "foto_url": "http://example.com/proyector.jpg",
            "especificaciones": {"lumenes": "3600", "resolucion": "1080p"},
        },
    )
    assert res_put.status_code == 200
    data = res_put.json()
    assert data["numero_serie"] is None
    assert data["color"] is None
    assert data["especificaciones"] == {"lumenes": "3600", "resolucion": "1080p"}

    res_buscar = client.get("/recursos", params={"filtro": "Proyector Epson Actualizado"})
    assert res_buscar.status_code == 200
    assert len(res_buscar.json()) == 1
    assert res_buscar.json()[0]["especificaciones"] == {
        "lumenes": "3600",
        "resolucion": "1080p",
    }
