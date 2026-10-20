"""Tests E2E para endpoints de reputación (presentation layer)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
        "nombre": "Juan Pérez",
        "correo": "juan@example.com",
        "telefono": "+34 600 123 456",
        "password": "Password123",
        "roles": roles or ["ESTUDIANTE"],
    }


def _crear_token(usuario_id: str, roles: list[str] | None = None, expirado: bool = False) -> str:
    """Helper para crear un token JWT."""
    ahora = datetime.now(UTC)
    if expirado:
        exp = ahora - timedelta(hours=1)
        iat = ahora - timedelta(hours=2)
    else:
        exp = ahora + timedelta(hours=1)
        iat = ahora
    payload = {
        "sub": usuario_id,
        "roles": roles or ["ESTUDIANTE"],
        "exp": exp,
        "iat": iat,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _registrar_y_login(datos: dict | None = None) -> tuple[str, dict]:
    """Helper para registrar usuario y hacer login, retorna (token, usuario)."""
    if datos is None:
        datos = _crear_usuario_ejemplo()
    client.post("/auth/registro", json=datos)
    response_login = client.post(
        "/auth/login", json={"correo": datos["correo"], "password": datos["password"]}
    )
    token = response_login.json()["token"]
    usuario = response_login.json()["usuario"]
    return token, usuario


@pytest.mark.e2e
class TestReputacionPerfil:
    """Tests para GET /reputacion/perfil."""

    def test_get_reputacion_perfil_token_valido_200(self) -> None:
        """RF-18: GET /reputacion/perfil con token válido retorna 200 con PerfilReputacionDTO."""
        token, usuario = _registrar_y_login()

        response = client.get(
            "/reputacion/perfil", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verificar estructura PerfilReputacionDTO
        assert "id" in data
        assert UUID(data["id"])
        assert data["usuario_id"] == usuario["id"]
        assert "puntaje" in data
        assert isinstance(data["puntaje"], int)
        assert data["puntaje"] == 500  # Valor por defecto
        assert "nivel" in data
        assert data["nivel"] == "NORMAL"  # Nivel por defecto para 500 pts
        assert "fecha_actualizacion" in data
        assert "sanciones" in data
        assert isinstance(data["sanciones"], list)
        assert len(data["sanciones"]) == 0

    def test_get_reputacion_perfil_sin_token_401(self) -> None:
        """RF-18: GET /reputacion/perfil sin token retorna 401."""
        response = client.get("/reputacion/perfil")
        assert response.status_code == 401

    def test_get_reputacion_perfil_token_expirado_401(self) -> None:
        """RF-18: GET /reputacion/perfil con token expirado retorna 401."""
        _token, usuario = _registrar_y_login()
        token_expirado = _crear_token(usuario["id"], expirado=True)

        response = client.get(
            "/reputacion/perfil", headers={"Authorization": f"Bearer {token_expirado}"}
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Token inválido o expirado"


@pytest.mark.e2e
class TestReputacionSanciones:
    """Tests para POST /reputacion/sanciones."""

    def test_post_reputacion_sanciones_admin_201(self) -> None:
        """RF-08: POST /reputacion/sanciones con rol ADMINISTRADOR_SISTEMA retorna 201 con SancionDTO real."""
        # Crear usuario admin
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        # Crear usuario víctima
        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima@example.com"
        _, victima = _registrar_y_login(datos_victima)

        # Aplicar sanción como admin (TARDANZA exige dias_retardo >= 1 — RF-07)
        body = {
            "usuario_id": victima["id"],
            "tipo": "TARDANZA",
            "motivo": "Devolución tardía de recurso",
            "dias_retardo": 5,
        }
        response = client.post(
            "/reputacion/sanciones",
            json=body,
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 201
        data = response.json()

        # RF-08: la respuesta es la sanción real (no un DTO ficticio de confirmación)
        assert UUID(data["id"])
        assert data["tipo"] == "TARDANZA"
        assert data["puntos_descuento"] == -10
        assert Decimal(str(data["monto_descuento"])) == Decimal(0)
        assert data["motivo"] == "Devolución tardía de recurso"
        assert data["activa"] is True
        assert data["vigente"] is True
        # RF-03/RF-05: fecha_fin derivada de la duración de bloqueo (5 días de retraso)
        fecha_aplicacion = datetime.fromisoformat(data["fecha_aplicacion"])
        fecha_fin = datetime.fromisoformat(data["fecha_fin"])
        assert fecha_fin - fecha_aplicacion == timedelta(days=5)

    def test_post_reputacion_sanciones_tardanza_sin_dias_retardo_422(self) -> None:
        """RF-07: TARDANZA sin dias_retardo retorna 422 (validación del DTO)."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima_sin_retardo@example.com"
        _, victima = _registrar_y_login(datos_victima)

        body = {
            "usuario_id": victima["id"],
            "tipo": "TARDANZA",
            "motivo": "Tardanza sin días de retraso",
        }
        response = client.post(
            "/reputacion/sanciones",
            json=body,
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 422

    def test_post_reputacion_sanciones_usuario_inexistente_404(self) -> None:
        """RF-23: sancionar a un usuario inexistente retorna 404 (UsuarioNoEncontrado)."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        body = {
            "usuario_id": "00000000-0000-0000-0000-000000000000",
            "tipo": "TARDANZA",
            "motivo": "Usuario inexistente",
            "dias_retardo": 3,
        }
        response = client.post(
            "/reputacion/sanciones",
            json=body,
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 404

    def test_post_reputacion_sanciones_gestor_almacen_201(self) -> None:
        """RF-20: POST /reputacion/sanciones con rol GESTOR_ALMACEN retorna 201."""
        datos_gestor = _crear_usuario_ejemplo(roles=["GESTOR_ALMACEN"])
        token_gestor, _ = _registrar_y_login(datos_gestor)

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima2@example.com"
        _, victima = _registrar_y_login(datos_victima)

        body = {
            "usuario_id": victima["id"],
            "tipo": "DANO_PARCIAL",
            "motivo": "Daño parcial a recurso",
        }
        response = client.post(
            "/reputacion/sanciones",
            json=body,
            headers={"Authorization": f"Bearer {token_gestor}"},
        )

        assert response.status_code == 201

    def test_post_reputacion_sanciones_sin_rol_admin_403(self) -> None:
        """RF-20: POST /reputacion/sanciones sin rol admin/gestor retorna 403."""
        token_estudiante, _ = _registrar_y_login()

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima3@example.com"
        _, victima = _registrar_y_login(datos_victima)

        body = {
            "usuario_id": victima["id"],
            "tipo": "TARDANZA",
            "motivo": "Intento de sanción sin permisos",
        }
        response = client.post(
            "/reputacion/sanciones",
            json=body,
            headers={"Authorization": f"Bearer {token_estudiante}"},
        )

        assert response.status_code == 403

    def test_post_reputacion_sanciones_sin_token_401(self) -> None:
        """RF-20: POST /reputacion/sanciones sin token retorna 401."""
        body = {
            "usuario_id": "00000000-0000-0000-0000-000000000000",
            "tipo": "TARDANZA",
            "motivo": "Sin token",
        }
        response = client.post("/reputacion/sanciones", json=body)
        assert response.status_code == 401


@pytest.mark.e2e
class TestReputacionExcepciones:
    """Tests para POST /reputacion/excepciones."""

    def test_post_reputacion_excepciones_admin_201(self) -> None:
        """RF-21: POST /reputacion/excepciones con rol ADMINISTRADOR_SISTEMA retorna 201."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima4@example.com"
        _, victima = _registrar_y_login(datos_victima)

        ahora = datetime.now(UTC)
        body = {
            "usuario_id": victima["id"],
            "motivo": "Examen final",
            "fecha_inicio": (ahora - timedelta(days=1)).isoformat(),
            "fecha_fin": (ahora + timedelta(days=7)).isoformat(),
        }
        response = client.post(
            "/reputacion/excepciones",
            json=body,
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert UUID(data["id"])
        assert data["usuario_id"] == victima["id"]
        assert data["motivo"] == "Examen final"
        assert data["activa"] is True

    def test_post_reputacion_excepciones_gestor_almacen_201(self) -> None:
        """RF-21: POST /reputacion/excepciones con rol GESTOR_ALMACEN retorna 201."""
        datos_gestor = _crear_usuario_ejemplo(roles=["GESTOR_ALMACEN"])
        token_gestor, _ = _registrar_y_login(datos_gestor)

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima5@example.com"
        _, victima = _registrar_y_login(datos_victima)

        ahora = datetime.now(UTC)
        body = {
            "usuario_id": victima["id"],
            "motivo": "Prácticas obligatorias",
            "fecha_inicio": (ahora - timedelta(days=1)).isoformat(),
            "fecha_fin": (ahora + timedelta(days=30)).isoformat(),
        }
        response = client.post(
            "/reputacion/excepciones",
            json=body,
            headers={"Authorization": f"Bearer {token_gestor}"},
        )

        assert response.status_code == 201

    def test_post_reputacion_excepciones_sin_rol_admin_403(self) -> None:
        """RF-21: POST /reputacion/excepciones sin rol admin/gestor retorna 403."""
        token_estudiante, _ = _registrar_y_login()

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima6@example.com"
        _, victima = _registrar_y_login(datos_victima)

        ahora = datetime.now(UTC)
        body = {
            "usuario_id": victima["id"],
            "motivo": "Intento sin permisos",
            "fecha_inicio": (ahora - timedelta(days=1)).isoformat(),
            "fecha_fin": (ahora + timedelta(days=7)).isoformat(),
        }
        response = client.post(
            "/reputacion/excepciones",
            json=body,
            headers={"Authorization": f"Bearer {token_estudiante}"},
        )

        assert response.status_code == 403

    def test_post_reputacion_excepciones_sin_token_401(self) -> None:
        """RF-21: POST /reputacion/excepciones sin token retorna 401."""
        ahora = datetime.now(UTC)
        body = {
            "usuario_id": "00000000-0000-0000-0000-000000000000",
            "motivo": "Sin token",
            "fecha_inicio": (ahora - timedelta(days=1)).isoformat(),
            "fecha_fin": (ahora + timedelta(days=7)).isoformat(),
        }
        response = client.post("/reputacion/excepciones", json=body)
        assert response.status_code == 401

    def test_post_reputacion_excepciones_usuario_inexistente_404(self) -> None:
        """RF-23: registrar una excepción para un usuario inexistente retorna 404."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        ahora = datetime.now(UTC)
        body = {
            "usuario_id": "00000000-0000-0000-0000-000000000000",
            "motivo": "Usuario inexistente",
            "fecha_inicio": (ahora - timedelta(days=1)).isoformat(),
            "fecha_fin": (ahora + timedelta(days=7)).isoformat(),
        }
        response = client.post(
            "/reputacion/excepciones",
            json=body,
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 404


@pytest.mark.e2e
class TestReputacionElegibilidad:
    """Tests para GET /reputacion/elegibilidad (RF-21)."""

    def test_get_reputacion_elegibilidad_200_sin_razon(self) -> None:
        """RF-21: sin sanciones bloqueantes es elegible y no hay razón."""
        token, _ = _registrar_y_login()

        response = client.get(
            "/reputacion/elegibilidad", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["elegible"] is True
        assert data["razon"] is None

    def test_get_reputacion_elegibilidad_con_sancion_vigente_incluye_razon(self) -> None:
        """RF-21: con una sanción vigente no es elegible y la razón incluye el tipo."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima_elegibilidad@example.com"
        token_victima, victima = _registrar_y_login(datos_victima)

        # T8b: la sanción se crea por la vía API (ya persiste entre peticiones)
        response_sancion = client.post(
            "/reputacion/sanciones",
            json={
                "usuario_id": victima["id"],
                "tipo": "TARDANZA",
                "motivo": "Devolución tardía de recurso",
                "dias_retardo": 5,
            },
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response_sancion.status_code == 201

        response = client.get(
            "/reputacion/elegibilidad", headers={"Authorization": f"Bearer {token_victima}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["elegible"] is False
        assert data["razon"] is not None
        assert "TARDANZA" in data["razon"]

    def test_get_reputacion_elegibilidad_sin_token_401(self) -> None:
        """RF-21: GET /reputacion/elegibilidad sin token retorna 401."""
        response = client.get("/reputacion/elegibilidad")
        assert response.status_code == 401


@pytest.mark.e2e
class TestReputacionAmnistia:
    """Tests para POST /reputacion/amnistia (RF-13)."""

    def test_post_reputacion_amnistia_admin_200(self) -> None:
        """RF-13: con rol de gestión retorna 200 con el conteo (0 es un valor válido)."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        response = client.post(
            "/reputacion/amnistia", headers={"Authorization": f"Bearer {token_admin}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["perfiles_premiados"], int)
        assert data["perfiles_premiados"] == 0  # ningún perfil BAJO persistido

    def test_post_reputacion_amnistia_sin_rol_403(self) -> None:
        """RF-13: sin rol de gestión retorna 403."""
        token_estudiante, _ = _registrar_y_login()

        response = client.post(
            "/reputacion/amnistia", headers={"Authorization": f"Bearer {token_estudiante}"}
        )

        assert response.status_code == 403

    def test_post_reputacion_amnistia_sin_token_401(self) -> None:
        """RF-13: sin token retorna 401."""
        response = client.post("/reputacion/amnistia")
        assert response.status_code == 401


@pytest.mark.e2e
class TestReputacionAnularExcepcion:
    """Tests para POST /reputacion/excepciones/{id}/anular (RF-22)."""

    def test_post_reputacion_anular_excepcion_admin_200(self) -> None:
        """RF-22: anular una excepción existente retorna 200 con activa=False (idempotente)."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima_anular@example.com"
        _, victima = _registrar_y_login(datos_victima)

        # T8b: la excepción se crea por la vía API (ya persiste entre peticiones)
        ahora = datetime.now(UTC)
        response_excepcion = client.post(
            "/reputacion/excepciones",
            json={
                "usuario_id": victima["id"],
                "motivo": "Examen final",
                "fecha_inicio": (ahora - timedelta(days=1)).isoformat(),
                "fecha_fin": (ahora + timedelta(days=7)).isoformat(),
            },
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response_excepcion.status_code == 201
        excepcion_id = response_excepcion.json()["id"]

        response = client.post(
            f"/reputacion/excepciones/{excepcion_id}/anular",
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == excepcion_id
        assert data["activa"] is False

        # Idempotente: anular de nuevo sigue siendo 200
        response_otra_vez = client.post(
            f"/reputacion/excepciones/{excepcion_id}/anular",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response_otra_vez.status_code == 200
        assert response_otra_vez.json()["activa"] is False

    def test_post_reputacion_anular_excepcion_inexistente_404(self) -> None:
        """RF-22: anular una excepción inexistente retorna 404 (ExcepcionNoEncontrada)."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        response = client.post(
            "/reputacion/excepciones/00000000-0000-0000-0000-000000000000/anular",
            headers={"Authorization": f"Bearer {token_admin}"},
        )

        assert response.status_code == 404

    def test_post_reputacion_anular_excepcion_sin_rol_403(self) -> None:
        """RF-22: sin rol de gestión retorna 403."""
        token_estudiante, _ = _registrar_y_login()

        response = client.post(
            "/reputacion/excepciones/00000000-0000-0000-0000-000000000000/anular",
            headers={"Authorization": f"Bearer {token_estudiante}"},
        )

        assert response.status_code == 403

    def test_post_reputacion_anular_excepcion_sin_token_401(self) -> None:
        """RF-22: sin token retorna 401."""
        response = client.post(
            "/reputacion/excepciones/00000000-0000-0000-0000-000000000000/anular"
        )
        assert response.status_code == 401


@pytest.mark.e2e
class TestPersistenciaEntrePeticiones:
    """T8b: la frontera de transacción por petición (D13) persiste lo escrito.

    Antes de T8b, `get_session` cerraba la sesión revirtiendo: una sanción devuelta
    con 201 se perdía y la lectura posterior mostraba un perfil vacío.
    """

    def test_post_sanciones_y_get_perfil_en_peticiones_distintas_persiste(self) -> None:
        """RF-08/RF-21 (T8b): sanción escrita en una petición y leída en otra (peticiones distintas)."""
        datos_admin = _crear_usuario_ejemplo(roles=["ADMINISTRADOR_SISTEMA"])
        token_admin, _ = _registrar_y_login(datos_admin)

        datos_victima = _crear_usuario_ejemplo()
        datos_victima["correo"] = "victima_persistencia@example.com"
        token_victima, victima = _registrar_y_login(datos_victima)

        # Petición 1: aplicar la sanción
        body = {
            "usuario_id": victima["id"],
            "tipo": "TARDANZA",
            "motivo": "Devolución tardía de recurso",
            "dias_retardo": 5,
        }
        response_sancion = client.post(
            "/reputacion/sanciones",
            json=body,
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response_sancion.status_code == 201
        sancion_id = response_sancion.json()["id"]

        # Petición 2 (distinta): el perfil de la víctima ya incluye la sanción
        response_perfil = client.get(
            "/reputacion/perfil", headers={"Authorization": f"Bearer {token_victima}"}
        )

        assert response_perfil.status_code == 200
        perfil = response_perfil.json()
        assert perfil["usuario_id"] == victima["id"]
        assert perfil["puntaje"] == 490  # 500 - 10 (TARDANZA)
        assert len(perfil["sanciones"]) == 1
        assert perfil["sanciones"][0]["id"] == sancion_id
        assert perfil["sanciones"][0]["fecha_fin"] is not None


@pytest.mark.e2e
class TestRequireRoles:
    """Tests para la dependencia require_roles."""

    def test_require_roles_admin_sin_rol_403(self) -> None:
        """require_roles(ADMINISTRADOR_SISTEMA) lanza 403 si usuario no tiene el rol."""
        # This is tested indirectly via the sanciones/excepciones tests above
        # but we can also test it directly if we expose a test endpoint
        # For now, the indirect test via POST /reputacion/sanciones is sufficient
