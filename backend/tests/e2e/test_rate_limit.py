"""Tests E2E para rate limiting y CORS."""

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
        usuario_model,
    )
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.e2e
def test_rate_limit_login_6_req_429() -> None:
    """6 peticiones rápidas a /auth/login → 429 en la 6ta."""
    # Hacemos 6 peticiones seguidas con credenciales inválidas
    # (el rate limit se aplica antes de validar credenciales)
    for i in range(6):
        response = client.post(
            "/auth/login",
            json={"correo": "test@example.com", "password": "wrongpassword"},
        )
        if i < 5:
            # Las primeras 5 deben pasar (401 por credenciales inválidas, no 429)
            assert response.status_code == 401, f"Petición {i+1}: esperado 401, got {response.status_code}"
        else:
            # La 6ta debe ser 429 (rate limited)
            assert response.status_code == 429, f"Petición 6: esperado 429, got {response.status_code}"
            assert "Rate limit exceeded" in response.text or "rate limit" in response.text.lower()


@pytest.mark.e2e
def test_rate_limit_registro_6_req_429() -> None:
    """6 peticiones rápidas a /auth/registro → 429 en la 6ta."""
    for i in range(6):
        response = client.post(
            "/auth/registro",
            json={
                "nombre": f"Test User {i}",
                "correo": f"test{i}@example.com",
                "password": "Password123",
            },
        )
        if i < 5:
            # Las primeras 5 deben pasar (201 o 400/409 por validaciones, no 429)
            assert response.status_code != 429, f"Petición {i+1}: no debería ser 429, got {response.status_code}"
        else:
            # La 6ta debe ser 429 (rate limited)
            assert response.status_code == 429, f"Petición 6: esperado 429, got {response.status_code}"
            assert "Rate limit exceeded" in response.text or "rate limit" in response.text.lower()


@pytest.mark.e2e
def test_cors_headers_presentes() -> None:
    """Verifica que Access-Control-Allow-Origin está presente en respuestas."""
    # Test con OPTIONS (preflight)
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Verificar headers CORS
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "access-control-allow-methods" in response.headers

    # Test con GET normal
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"