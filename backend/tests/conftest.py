"""Configuración compartida para todos los tests (unit, integration, e2e)."""

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from datetime import UTC, datetime, timedelta

from prestamos_recursos.config import settings
from prestamos_recursos.main import app
from prestamos_recursos.shared.database import Base, engine, SessionLocal


@pytest.fixture(scope="session")
def client() -> TestClient:
    """TestClient compartido para tests que no necesitan BD real."""
    return TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """
    Sesión de BD real para tests de integración.
    Requiere: docker compose up -d
    Crea tablas antes y limpia después.
    """
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_token(db_session):
    """
    Token JWT de un usuario ESTUDIANTE creado en el test.
    Requiere BD real (docker compose up -d).
    """
    from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import AutenticacionService
    from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import CrearUsuarioDTO
    from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import SqlUsuarioRepository

    usuario_repo = SqlUsuarioRepository(db_session)
    auth_service = AutenticacionService(usuario_repo)

    datos = CrearUsuarioDTO(
        nombre="Test Estudiante",
        correo="estudiante@test.com",
        telefono="+34 600 123 456",
        password="Password123",
    )
    resultado = auth_service.registrar_usuario(datos)
    return resultado.token


@pytest.fixture
def admin_token(db_session):
    """
    Token JWT de un usuario ADMINISTRADOR_SISTEMA creado en el test.
    Requiere BD real (docker compose up -d).
    """
    from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import AutenticacionService
    from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import CrearUsuarioDTO
    from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
    from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import SqlUsuarioRepository

    usuario_repo = SqlUsuarioRepository(db_session)
    auth_service = AutenticacionService(usuario_repo)

    datos = CrearUsuarioDTO(
        nombre="Test Admin",
        correo="admin@test.com",
        telefono="+34 600 999 999",
        password="Password123",
        roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
    )
    resultado = auth_service.registrar_usuario(datos)
    return resultado.token


@pytest.fixture
def expired_token():
    """Token JWT expirado para tests de validación."""
    payload = {
        "sub": "00000000-0000-0000-0000-000000000000",
        "roles": ["ESTUDIANTE"],
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(hours=2),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@pytest.fixture
def invalid_token():
    """Token JWT mal firmado para tests de validación."""
    return "token.mal.firmado"


# Fixtures helpers para tests E2E que usan TestClient directamente
@pytest.fixture
def e2e_client():
    """TestClient para tests E2E."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test to avoid cross-test interference."""
    from prestamos_recursos.shared.rate_limit import limiter
    limiter.reset()
    yield
    limiter.reset()