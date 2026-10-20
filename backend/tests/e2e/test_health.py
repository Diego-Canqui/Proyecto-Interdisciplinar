from fastapi.testclient import TestClient

from prestamos_recursos.main import app

client = TestClient(app)


import pytest


@pytest.mark.e2e
def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
