"""Tests de integración para AutenticacionService (application + DB)."""
from __future__ import annotations

import time
from uuid import UUID

import pytest
from fastapi import HTTPException

from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import (
    AutenticacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
    LoginDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import (
    SqlUsuarioRepository,
)
from prestamos_recursos.shared.database import Base, engine, SessionLocal


@pytest.fixture(scope="function")
def db_session():
    """Crea una sesión de BD limpia para cada test."""
    # Crear tablas
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Limpiar tablas
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def usuario_repo(db_session):
    return SqlUsuarioRepository(db_session)


@pytest.fixture
def auth_service(usuario_repo):
    return AutenticacionService(usuario_repo)


class TestRegistrarUsuario:
    """Tests para registrar_usuario."""

    def test_registrar_usuario_persiste_con_hash_uuid_roles(self, auth_service):
        """RF-01: Registro persiste usuario con hash, UUID, roles por defecto."""
        datos = CrearUsuarioDTO(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )

        resultado = auth_service.registrar_usuario(datos)

        assert isinstance(resultado.token, str)
        assert len(resultado.token) > 0
        assert isinstance(resultado.usuario.id, UUID)
        assert resultado.usuario.nombre == "Juan Pérez"
        assert resultado.usuario.correo == "juan@example.com"
        assert resultado.usuario.telefono == "+34 600 123 456"
        assert resultado.usuario.roles == [RolUsuario.ESTUDIANTE]
        assert resultado.usuario.estado is True

        # Verificar que el password no está en el DTO
        assert not hasattr(resultado.usuario, "password_hash")

    def test_registrar_usuario_correo_duplicado_409(self, auth_service):
        """RF-02: Registro con correo duplicado lanza 409."""
        datos = CrearUsuarioDTO(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )
        auth_service.registrar_usuario(datos)

        with pytest.raises(HTTPException) as exc_info:
            auth_service.registrar_usuario(datos)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Correo ya registrado"

    def test_registrar_usuario_email_invalido_400(self, auth_service):
        """RF-03: Registro con email inválido lanza 400."""
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                nombre="Juan Pérez",
                correo="no-es-email",
                telefono="+34 600 123 456",
                password="Password123",
            )

        # Pydantic validation error
        assert "value is not a valid email address" in str(exc_info.value).lower()

    def test_registrar_usuario_password_corta_400(self, auth_service):
        """RF-04: Registro con password < 8 chars o sin complejidad lanza 400."""
        # Password muy corta
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                nombre="Juan Pérez",
                correo="juan@example.com",
                telefono="+34 600 123 456",
                password="Pass1",
            )
        assert "string should have at least 8 characters" in str(exc_info.value).lower()

        # Password sin mayúscula
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                nombre="Juan Pérez",
                correo="juan@example.com",
                telefono="+34 600 123 456",
                password="password123",
            )
        assert "string does not match pattern" in str(exc_info.value).lower()

        # Password sin minúscula
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                nombre="Juan Pérez",
                correo="juan@example.com",
                telefono="+34 600 123 456",
                password="PASSWORD123",
            )
        assert "string does not match pattern" in str(exc_info.value).lower()

        # Password sin dígito
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                nombre="Juan Pérez",
                correo="juan@example.com",
                telefono="+34 600 123 456",
                password="Password",
            )
        assert "string does not match pattern" in str(exc_info.value).lower()

    def test_registrar_usuario_campos_faltantes_400(self, auth_service):
        """RF-05: Registro con campos obligatorios faltantes lanza 400."""
        # Falta nombre
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                correo="juan@example.com",
                telefono="+34 600 123 456",
                password="Password123",
            )
        assert "field required" in str(exc_info.value).lower()

        # Falta correo
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                nombre="Juan Pérez",
                telefono="+34 600 123 456",
                password="Password123",
            )
        assert "field required" in str(exc_info.value).lower()

        # Falta password
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                nombre="Juan Pérez",
                correo="juan@example.com",
                telefono="+34 600 123 456",
            )
        assert "field required" in str(exc_info.value).lower()

    def test_registrar_usuario_telefono_invalido_400(self, auth_service):
        """RF-06: Registro con teléfono inválido lanza 400."""
        with pytest.raises(Exception) as exc_info:
            CrearUsuarioDTO(
                nombre="Juan Pérez",
                correo="juan@example.com",
                telefono="123",  # Inválido: muy corto, no coincide regex
                password="Password123",
            )
        assert "string does not match pattern" in str(exc_info.value).lower()

    def test_registrar_usuario_con_roles_personalizados(self, auth_service):
        """Registro con roles personalizados los respeta."""
        datos = CrearUsuarioDTO(
            nombre="Admin User",
            correo="admin@example.com",
            telefono=None,
            password="Password123",
            roles=[RolUsuario.ADMIN, RolUsuario.BIBLIOTECARIO],
        )

        resultado = auth_service.registrar_usuario(datos)

        assert resultado.usuario.roles == [RolUsuario.ADMIN, RolUsuario.BIBLIOTECARIO]


class TestLogin:
    """Tests para login."""

    def test_login_devuelve_jwt_valido(self, auth_service):
        """RF-07: Login con credenciales correctas devuelve JWT válido."""
        # Registrar usuario primero
        datos_registro = CrearUsuarioDTO(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )
        auth_service.registrar_usuario(datos_registro)

        # Login
        datos_login = LoginDTO(correo="juan@example.com", password="Password123")
        resultado = auth_service.login(datos_login)

        assert isinstance(resultado.token, str)
        assert len(resultado.token) > 0
        assert resultado.usuario.correo == "juan@example.com"
        assert resultado.usuario.nombre == "Juan Pérez"

        # Verificar que el token es un JWT válido (3 partes separadas por .)
        partes = resultado.token.split(".")
        assert len(partes) == 3

    def test_login_credenciales_invalidas_401(self, auth_service):
        """RF-08: Login con credenciales incorrectas lanza 401 genérico."""
        # Usuario no existe
        datos_login = LoginDTO(correo="noexiste@example.com", password="Password123")
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login(datos_login)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Credenciales inválidas"

        # Registrar usuario
        datos_registro = CrearUsuarioDTO(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )
        auth_service.registrar_usuario(datos_registro)

        # Password incorrecto
        datos_login = LoginDTO(correo="juan@example.com", password="WrongPassword123")
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login(datos_login)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Credenciales inválidas"


class TestValidarToken:
    """Tests para validar_token."""

    def test_validar_token_acepta_valido_rechaza_expirado(self, auth_service):
        """RF-11: validar_token acepta token válido, rechaza expirado/mal firmado."""
        # Registrar y login
        datos_registro = CrearUsuarioDTO(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )
        resultado = auth_service.registrar_usuario(datos_registro)
        token = resultado.token

        # Token válido
        usuario_id = auth_service.validar_token(token)
        assert isinstance(usuario_id, UUID)
        assert usuario_id == resultado.usuario.id

        # Token mal formado
        assert auth_service.validar_token("token.invalido") is None

        # Token con firma incorrecta (simular otro secret)
        from jose import jwt
        from prestamos_recursos.config import settings

        payload_falso = {"sub": str(resultado.usuario.id), "roles": ["ESTUDIANTE"]}
        token_falso = jwt.encode(payload_falso, "otro-secret", algorithm="HS256")
        assert auth_service.validar_token(token_falso) is None


class TestObtenerUsuarioPorToken:
    """Tests para obtener_usuario_por_token."""

    def test_obtener_usuario_por_token_funciona(self, auth_service):
        """RF-10: obtener_usuario_por_token devuelve UsuarioDTO con token válido."""
        # Registrar y login
        datos_registro = CrearUsuarioDTO(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )
        resultado = auth_service.registrar_usuario(datos_registro)
        token = resultado.token

        # Obtener usuario por token
        usuario_dto = auth_service.obtener_usuario_por_token(token)

        assert usuario_dto is not None
        assert usuario_dto.id == resultado.usuario.id
        assert usuario_dto.nombre == "Juan Pérez"
        assert usuario_dto.correo == "juan@example.com"
        assert usuario_dto.telefono == "+34 600 123 456"
        assert usuario_dto.roles == [RolUsuario.ESTUDIANTE]
        assert usuario_dto.estado is True

    def test_obtener_usuario_por_token_invalido_devuelve_none(self, auth_service):
        """Token inválido devuelve None."""
        assert auth_service.obtener_usuario_por_token("token.invalido") is None

    def test_obtener_usuario_por_token_usuario_inexistente_devuelve_none(
        self, auth_service
    ):
        """Token válido pero usuario borrado devuelve None."""
        from jose import jwt
        from datetime import datetime, timedelta
        from prestamos_recursos.config import settings

        # Token con sub de UUID inexistente
        payload = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "roles": ["ESTUDIANTE"],
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        assert auth_service.obtener_usuario_por_token(token) is None