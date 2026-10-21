"""Tests E2E para endpoints de gestión de usuarios (presentation layer)."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from prestamos_recursos.main import app
from prestamos_recursos.shared.database import Base, engine

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Crear tablas antes de cada test y limpiar después."""
    # Import models to register them
    from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models import (  # noqa: F401
        excepcion_academica_model,
        perfil_reputacion_model,
        usuario_model,
    )
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _crear_usuario_ejemplo(roles: list[str] | None = None) -> dict:
    """Helper para crear datos de usuario válidos."""
    return {
        "nombre": "Ana Gestora",
        "correo": "ana@example.com",
        "telefono": "+34 600 123 456",
        "password": "Password123",
        "roles": roles or ["ESTUDIANTE"],
    }


def _registrar_y_login(datos: dict | None = None) -> tuple[str, dict]:
    """Registra un usuario por la vía pública y hace login, retorna (token, usuario)."""
    if datos is None:
        datos = _crear_usuario_ejemplo()
    client.post("/auth/registro", json=datos)
    response_login = client.post(
        "/auth/login", json={"correo": datos["correo"], "password": datos["password"]}
    )
    body = response_login.json()
    return body["token"], body["usuario"]


def _token_de(roles: list[str]) -> str:
    """Registra un usuario con los roles indicados y devuelve su token."""
    token, _ = _registrar_y_login(_crear_usuario_ejemplo(roles=roles))
    return token


@pytest.mark.e2e
class TestCrearUsuarioEndpoint:
    """POST /usuarios (RF-16/RF-17)."""

    def test_post_usuarios_admin_201_y_login_inmediato_200(self) -> None:
        """RF-16: 201 con UsuarioDTO real y login inmediato con la contraseña indicada."""
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])

        body = {
            "nombre": "Nuevo Docente",
            "correo": "nuevo@example.com",
            "telefono": "+34 600 222 333",
            "password": "Password123",
        }
        response = client.post(
            "/usuarios", json=body, headers={"Authorization": f"Bearer {token_admin}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert UUID(data["id"])
        assert data["nombre"] == "Nuevo Docente"
        assert data["correo"] == "nuevo@example.com"
        assert data["roles"] == ["ESTUDIANTE"]  # default del DTO
        assert data["estado"] is True
        assert "password_hash" not in data

        login = client.post(
            "/auth/login", json={"correo": "nuevo@example.com", "password": "Password123"}
        )

        assert login.status_code == 200
        assert login.json()["usuario"]["id"] == data["id"]

    def test_post_usuarios_gestor_almacen_201(self) -> None:
        """RF-17: GESTOR_ALMACEN puede dar de alta usuarios."""
        token_gestor = _token_de(["GESTOR_ALMACEN"])

        response = client.post(
            "/usuarios",
            json={
                "nombre": "Otro Usuario",
                "correo": "otro@example.com",
                "password": "Password123",
            },
            headers={"Authorization": f"Bearer {token_gestor}"},
        )

        assert response.status_code == 201

    def test_post_usuarios_correo_duplicado_409(self) -> None:
        """RF-16: un correo ya registrado responde 409."""
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])

        response = client.post(
            "/usuarios",
            json={
                "nombre": "Duplicado",
                "correo": "ana@example.com",
                "password": "Password123",
            },
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 409

    def test_post_usuarios_password_debil_422_sin_crear(self) -> None:
        """RF-16: contraseña débil responde 422 y el usuario no se crea."""
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])

        response = client.post(
            "/usuarios",
            json={"nombre": "Debil", "correo": "debil@example.com", "password": "debil"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 422

        login = client.post(
            "/auth/login", json={"correo": "debil@example.com", "password": "debil"}
        )
        assert login.status_code == 401

    def test_post_usuarios_sin_token_401(self) -> None:
        """RF-17: sin token responde 401."""
        response = client.post(
            "/usuarios",
            json={"nombre": "Sin Token", "correo": "sintoken@example.com", "password": "Password123"},
        )

        assert response.status_code == 401

    def test_post_usuarios_con_rol_estudiante_403(self) -> None:
        """RF-17: con rol ESTUDIANTE responde 403."""
        token_estudiante = _token_de(["ESTUDIANTE"])

        response = client.post(
            "/usuarios",
            json={"nombre": "Prohibido", "correo": "prohibido@example.com", "password": "Password123"},
            headers={"Authorization": f"Bearer {token_estudiante}"},
        )

        assert response.status_code == 403


@pytest.mark.e2e
class TestListarUsuariosEndpoint:
    """GET /usuarios (RF-17)."""

    def test_get_usuarios_admin_200(self) -> None:
        """RF-17: con rol de gestión devuelve la lista de usuarios sin hashes."""
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])

        response = client.get("/usuarios", headers={"Authorization": f"Bearer {token_admin}"})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(usuario["correo"] == "ana@example.com" for usuario in data)
        assert all("password_hash" not in usuario for usuario in data)

    def test_get_usuarios_sin_token_401(self) -> None:
        """RF-17: sin token responde 401."""
        response = client.get("/usuarios")
        assert response.status_code == 401

    def test_get_usuarios_con_rol_estudiante_403(self) -> None:
        """RF-17: con rol ESTUDIANTE responde 403."""
        token_estudiante = _token_de(["ESTUDIANTE"])

        response = client.get(
            "/usuarios", headers={"Authorization": f"Bearer {token_estudiante}"}
        )

        assert response.status_code == 403
