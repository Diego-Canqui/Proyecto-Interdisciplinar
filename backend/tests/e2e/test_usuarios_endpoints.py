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
    from prestamos_recursos.contexts.catalogo.infrastructure.models import (
        recurso_model,  # noqa: F401
    )
    from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models import (  # noqa: F401
        excepcion_academica_model,
        perfil_reputacion_model,
        usuario_model,
    )
    from prestamos_recursos.contexts.prestamos.infrastructure.models import (  # noqa: F401
        checklist_model,
        garantia_model,
        prestamo_model,
    )
    from prestamos_recursos.contexts.reservas.infrastructure.models import (
        reserva_model,  # noqa: F401
    )

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _crear_usuario_ejemplo(roles: list[str] | None = None, correo: str = "ana@example.com") -> dict:
    """Helper para crear datos de usuario válidos."""
    return {
        "nombre": "Ana Gestora",
        "correo": correo,
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


@pytest.mark.e2e
class TestJerarquiaRolesCrearUsuarioEndpoint:
    """RF-09: Control jerárquico de roles en POST /usuarios."""

    def test_gestor_crear_usuario_rol_solicitante_201(self) -> None:
        """RF-09: Un gestor de almacén puede asignar roles solicitantes."""
        token_gestor = _token_de(["GESTOR_ALMACEN"])

        body = {
            "nombre": "Docente Nuevo",
            "correo": "docente_nuevo@example.com",
            "password": "Password123",
            "roles": ["DOCENTE"],
        }
        response = client.post(
            "/usuarios", json=body, headers={"Authorization": f"Bearer {token_gestor}"}
        )
        assert response.status_code == 201
        assert response.json()["roles"] == ["DOCENTE"]

    def test_gestor_crear_usuario_rol_gestion_403(self) -> None:
        """RF-09: Un gestor de almacén recibe 403 si intenta asignar roles de gestión."""
        token_gestor = _token_de(["GESTOR_ALMACEN"])

        body = {
            "nombre": "Intento Gestor",
            "correo": "intento_gestor@example.com",
            "password": "Password123",
            "roles": ["GESTOR_ALMACEN"],
        }
        response = client.post(
            "/usuarios", json=body, headers={"Authorization": f"Bearer {token_gestor}"}
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "El gestor de almacén solo puede asignar roles solicitantes"

        body["roles"] = ["ADMINISTRADOR_SISTEMA"]
        response2 = client.post(
            "/usuarios", json=body, headers={"Authorization": f"Bearer {token_gestor}"}
        )
        assert response2.status_code == 403
        assert response2.json()["detail"] == "El gestor de almacén solo puede asignar roles solicitantes"

    def test_admin_crear_usuario_rol_gestion_201(self) -> None:
        """RF-09: Un administrador puede asignar cualquier rol, incluidos de gestión."""
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])

        body = {
            "nombre": "Nuevo Admin",
            "correo": "nuevo_admin@example.com",
            "password": "Password123",
            "roles": ["ADMINISTRADOR_SISTEMA"],
        }
        response = client.post(
            "/usuarios", json=body, headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert response.status_code == 201
        assert response.json()["roles"] == ["ADMINISTRADOR_SISTEMA"]


@pytest.mark.e2e
class TestCambiarRolUsuarioEndpoint:
    """PATCH /usuarios/{id}/rol (RF-10)."""

    def test_admin_cambiar_rol_exito_200(self) -> None:
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])
        _, user_estudiante = _registrar_y_login(_crear_usuario_ejemplo(correo="estudiante1@example.com"))

        response = client.patch(
            f"/usuarios/{user_estudiante['id']}/rol",
            json={"rol": "DOCENTE"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        assert response.json()["roles"] == ["DOCENTE"]

    def test_admin_cambiar_rol_autoproteccion_409(self) -> None:
        token_admin, user_admin = _registrar_y_login(
            _crear_usuario_ejemplo(correo="admin_self@example.com", roles=["ADMINISTRADOR_SISTEMA"])
        )

        response = client.patch(
            f"/usuarios/{user_admin['id']}/rol",
            json={"rol": "ESTUDIANTE"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "No puedes quitarte el rol de administrador a ti mismo"

    def test_gestor_cambiar_rol_403(self) -> None:
        token_gestor = _token_de(["GESTOR_ALMACEN"])
        _, user_estudiante = _registrar_y_login(_crear_usuario_ejemplo(correo="estudiante2@example.com"))

        response = client.patch(
            f"/usuarios/{user_estudiante['id']}/rol",
            json={"rol": "DOCENTE"},
            headers={"Authorization": f"Bearer {token_gestor}"},
        )
        assert response.status_code == 403

    def test_cambiar_rol_usuario_inexistente_404(self) -> None:
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])
        response = client.patch(
            "/usuarios/00000000-0000-0000-0000-000000000000/rol",
            json={"rol": "DOCENTE"},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 404


@pytest.mark.e2e
class TestCambiarEstadoUsuarioEndpoint:
    """PATCH /usuarios/{id}/estado (RF-11)."""

    def test_admin_desactivar_y_activar_200(self) -> None:
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])
        _, user_estudiante = _registrar_y_login(_crear_usuario_ejemplo(correo="estudiante3@example.com"))

        # Desactivar
        res1 = client.patch(
            f"/usuarios/{user_estudiante['id']}/estado",
            json={"estado": False},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res1.status_code == 200
        assert res1.json()["estado"] is False

        # Reactivar
        res2 = client.patch(
            f"/usuarios/{user_estudiante['id']}/estado",
            json={"estado": True},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res2.status_code == 200
        assert res2.json()["estado"] is True

    def test_admin_desactivarse_a_si_mismo_409(self) -> None:
        token_admin, user_admin = _registrar_y_login(
            _crear_usuario_ejemplo(correo="admin_self2@example.com", roles=["ADMINISTRADOR_SISTEMA"])
        )

        response = client.patch(
            f"/usuarios/{user_admin['id']}/estado",
            json={"estado": False},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "No puedes desactivar tu propia cuenta"

    def test_gestor_cambiar_estado_403(self) -> None:
        token_gestor = _token_de(["GESTOR_ALMACEN"])
        _, user_estudiante = _registrar_y_login(_crear_usuario_ejemplo(correo="estudiante4@example.com"))

        response = client.patch(
            f"/usuarios/{user_estudiante['id']}/estado",
            json={"estado": False},
            headers={"Authorization": f"Bearer {token_gestor}"},
        )
        assert response.status_code == 403


@pytest.mark.e2e
class TestEliminarUsuarioEndpoint:
    """DELETE /usuarios/{id} (RF-12)."""

    def test_admin_eliminar_usuario_sin_operaciones_200(self) -> None:
        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])
        _, user_estudiante = _registrar_y_login(_crear_usuario_ejemplo(correo="estudiante5@example.com"))

        response = client.delete(
            f"/usuarios/{user_estudiante['id']}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 200
        assert response.json() == {"detalle": "Usuario eliminado correctamente"}

        # Verificar que ya no existe
        res_del = client.delete(
            f"/usuarios/{user_estudiante['id']}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res_del.status_code == 404

    def test_admin_eliminar_a_si_mismo_409(self) -> None:
        token_admin, user_admin = _registrar_y_login(
            _crear_usuario_ejemplo(correo="admin_self3@example.com", roles=["ADMINISTRADOR_SISTEMA"])
        )

        response = client.delete(
            f"/usuarios/{user_admin['id']}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "No puedes eliminar tu propia cuenta"

    def test_gestor_eliminar_usuario_403(self) -> None:
        token_gestor = _token_de(["GESTOR_ALMACEN"])
        _, user_estudiante = _registrar_y_login(_crear_usuario_ejemplo(correo="estudiante6@example.com"))

        response = client.delete(
            f"/usuarios/{user_estudiante['id']}",
            headers={"Authorization": f"Bearer {token_gestor}"},
        )
        assert response.status_code == 403

    def test_admin_eliminar_usuario_con_prestamo_activo_409(self) -> None:
        """RF-12: Intento de eliminar usuario con préstamo activo responde 409."""
        from datetime import UTC, datetime, timedelta
        from uuid import uuid4

        from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import (
            EstadoPrestamo,
        )
        from prestamos_recursos.contexts.prestamos.infrastructure.models.prestamo_model import (
            PrestamoModel,
        )
        from prestamos_recursos.shared.database import SessionLocal

        token_admin = _token_de(["ADMINISTRADOR_SISTEMA"])
        _, user_estudiante = _registrar_y_login(_crear_usuario_ejemplo(correo="estudiante7@example.com"))
        user_id = UUID(user_estudiante["id"])

        with SessionLocal() as session:
            prestamo = PrestamoModel(
                id=uuid4(),
                reserva_id=uuid4(),
                recurso_id=uuid4(),
                usuario_id=user_id,
                estado=EstadoPrestamo.ACTIVO,
                fecha_inicio=datetime.now(UTC),
                fecha_fin=datetime.now(UTC) + timedelta(days=2),
            )
            session.add(prestamo)
            session.commit()

        response = client.delete(
            f"/usuarios/{user_id}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "No se puede eliminar un usuario con reservas activas o préstamos en curso"


