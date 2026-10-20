"""Configuración compartida para tests E2E."""

import pytest

from prestamos_recursos.shared.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test to avoid cross-test interference."""
    limiter.reset()
    yield
    limiter.reset()