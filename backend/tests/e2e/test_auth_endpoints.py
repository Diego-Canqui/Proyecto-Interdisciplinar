"""Tests E2E para endpoints de autenticación (presentation layer)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from prestamos_recursos.config import settings
from prestamos_recursos.main import app
from prestamos_recursos.shared.database import Base, engine

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Crear tablas antes de cada test y limpiar después."""
    # Import models to register them
    from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models import (  # noqa: F401
        usuario_model,
    )
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _crear_usuario_ejemplo() -> dict:
    """Helper para crear datos de usuario válidos."""
    return {
        "nombre": "Juan Pérez",
        "correo": "juan@example.com",
        "telefono": "+34 600 123 456",
        "password": "Password123",
    }


def _crear_token_expirado(usuario_id: str) -> str:
    """Helper para crear un token JWT expirado."""
    payload = {
        "sub": usuario_id,
        "roles": ["ESTUDIANTE"],
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(hours=2),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@pytest.mark.e2e
class TestAuthRegistro:
    """Tests para POST /auth/registro."""

    def test_post_auth_registro_201_token_dto(self) -> None:
        """RF-01: POST /auth/registro retorna 201 con TokenDTO (JWT + UsuarioDTO sin passwordHash)."""
        datos = _crear_usuario_ejemplo()

        response = client.post("/auth/registro", json=datos)

        assert response.status_code == 201
        data = response.json()

        # Verificar estructura TokenDTO
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0

        # Verificar estructura UsuarioDTO
        assert "usuario" in data
        usuario = data["usuario"]
        assert "id" in usuario
        assert UUID(usuario["id"])  # UUID válido
        assert usuario["nombre"] == "Juan Pérez"
        assert usuario["correo"] == "juan@example.com"
        assert usuario["telefono"] == "+34 600 123 456"
        assert usuario["roles"] == ["ESTUDIANTE"]
        assert usuario["estado"] is True

        # Verificar que NO hay password_hash
        assert "password_hash" not in usuario
        assert "password" not in usuario

    def test_post_auth_registro_correo_duplicado_409(self) -> None:
        """RF-02: POST /auth/registro con correo duplicado retorna 409."""
        datos = _crear_usuario_ejemplo()

        # Primera registro: OK
        response1 = client.post("/auth/registro", json=datos)
        assert response1.status_code == 201

        # Segunda registro con mismo correo: 409
        response2 = client.post("/auth/registro", json=datos)
        assert response2.status_code == 409
        assert response2.json()["detail"] == "Correo ya registrado"

    def test_post_auth_registro_validaciones_400(self) -> None:
        """RF-03, RF-04, RF-05, RF-06: POST /auth/registro valida campos y retorna 422 (validación Pydantic)."""
        base = _crear_usuario_ejemplo()

        # RF-03: Email inválido
        datos = {**base, "correo": "no-es-email"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422

        # RF-04: Password muy corta
        datos = {**base, "password": "Pass1"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422

        # RF-04: Password sin mayúscula
        datos = {**base, "password": "password123"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422

        # RF-04: Password sin minúscula
        datos = {**base, "password": "PASSWORD123"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422

        # RF-04: Password sin dígito
        datos = {**base, "password": "Password"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422

        # RF-05: Falta nombre
        datos = {k: v for k, v in base.items() if k != "nombre"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422

        # RF-05: Falta correo
        datos = {k: v for k, v in base.items() if k != "correo"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422

        # RF-05: Falta password
        datos = {k: v for k, v in base.items() if k != "password"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422

        # RF-06: Teléfono inválido
        datos = {**base, "telefono": "123"}
        response = client.post("/auth/registro", json=datos)
        assert response.status_code == 422


@pytest.mark.e2e
class TestAuthLogin:
    """Tests para POST /auth/login."""

    def test_post_auth_login_200_token_dto(self) -> None:
        """RF-07: POST /auth/login retorna 200 con TokenDTO."""
        # Primero registrar usuario
        datos_registro = _crear_usuario_ejemplo()
        client.post("/auth/registro", json=datos_registro)

        # Luego login
        datos_login = {"correo": "juan@example.com", "password": "Password123"}
        response = client.post("/auth/login", json=datos_login)

        assert response.status_code == 200
        data = response.json()

        # Verificar estructura TokenDTO
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0

        # Verificar estructura UsuarioDTO
        assert "usuario" in data
        usuario = data["usuario"]
        assert "id" in usuario
        assert UUID(usuario["id"])
        assert usuario["nombre"] == "Juan Pérez"
        assert usuario["correo"] == "juan@example.com"
        assert usuario["telefono"] == "+34 600 123 456"
        assert usuario["roles"] == ["ESTUDIANTE"]
        assert usuario["estado"] is True
        assert "password_hash" not in usuario

    def test_post_auth_login_credenciales_invalidas_401(self) -> None:
        """RF-08: POST /auth/login con credenciales inválidas retorna 401 genérico."""
        # Usuario no existe
        datos_login = {"correo": "noexiste@example.com", "password": "Password123"}
        response = client.post("/auth/login", json=datos_login)
        assert response.status_code == 401
        assert response.json()["detail"] == "Credenciales inválidas"

        # Registrar usuario
        datos_registro = _crear_usuario_ejemplo()
        client.post("/auth/registro", json=datos_registro)

        # Password incorrecto
        datos_login = {"correo": "juan@example.com", "password": "WrongPassword123"}
        response = client.post("/auth/login", json=datos_login)
        assert response.status_code == 401
        assert response.json()["detail"] == "Credenciales inválidas"


@pytest.mark.e2e
class TestAuthLogout:
    """Tests para POST /auth/logout."""

    def test_post_auth_logout_200(self) -> None:
        """RF-09: POST /auth/logout retorna 200 con mensaje."""
        response = client.post("/auth/logout")
        assert response.status_code == 200
        assert response.json() == {"message": "Sesión cerrada"}


@pytest.mark.e2e
class TestAuthPerfil:
    """Tests para GET /auth/perfil."""

    def test_get_auth_perfil_token_valido_200(self) -> None:
        """RF-10: GET /auth/perfil con token válido retorna 200 con UsuarioDTO."""
        # Registrar y login para obtener token
        datos_registro = _crear_usuario_ejemplo()
        client.post("/auth/registro", json=datos_registro)

        datos_login = {"correo": "juan@example.com", "password": "Password123"}
        response_login = client.post("/auth/login", json=datos_login)
        token = response_login.json()["token"]

        # Llamar a /perfil con token válido
        response = client.get("/auth/perfil", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        usuario = response.json()
        assert "id" in usuario
        assert UUID(usuario["id"])
        assert usuario["nombre"] == "Juan Pérez"
        assert usuario["correo"] == "juan@example.com"
        assert usuario["telefono"] == "+34 600 123 456"
        assert usuario["roles"] == ["ESTUDIANTE"]
        assert usuario["estado"] is True
        assert "password_hash" not in usuario

    def test_get_auth_perfil_token_expirado_401(self) -> None:
        """RF-11: GET /auth/perfil con token expirado retorna 401."""
        # Registrar usuario para obtener un ID real
        datos_registro = _crear_usuario_ejemplo()
        response_registro = client.post("/auth/registro", json=datos_registro)
        usuario_id = response_registro.json()["usuario"]["id"]

        # Crear token expirado
        token_expirado = _crear_token_expirado(usuario_id)

        response = client.get("/auth/perfil", headers={"Authorization": f"Bearer {token_expirado}"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Token inválido o expirado"

    def test_get_auth_perfil_token_invalido_401(self) -> None:
        """RF-11: GET /auth/perfil con token mal firmado retorna 401."""
        token_invalido = "token.mal.firmado"

        response = client.get("/auth/perfil", headers={"Authorization": f"Bearer {token_invalido}"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Token inválido o expirado"

    def test_get_auth_perfil_sin_token_401(self) -> None:
        """RF-11: GET /auth/perfil sin token retorna 401."""
        response = client.get("/auth/perfil")

        assert response.status_code == 401

    def test_get_auth_perfil_usuario_inexistente_401(self) -> None:
        """RF-11: GET /auth/perfil con token válido pero usuario borrado retorna 401."""
        # Crear token con UUID inexistente
        payload = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "roles": ["ESTUDIANTE"],
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        response = client.get("/auth/perfil", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Token inválido o expirado"