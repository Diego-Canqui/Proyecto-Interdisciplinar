"""Tests de integración para UsuarioService (application + DB)."""
from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import (
    AutenticacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
    LoginDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.usuario_service import (
    UsuarioService,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import (
    SqlUsuarioRepository,
)
from prestamos_recursos.shared.database import Base, SessionLocal, engine


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
def usuario_service(usuario_repo):
    return UsuarioService(usuario_repo)


@pytest.fixture
def auth_service(usuario_repo):
    return AutenticacionService(usuario_repo)


def _datos(**overrides) -> CrearUsuarioDTO:
    """Datos válidos para el alta de gestión, con overrides opcionales."""
    base = {
        "nombre": "Ana Gestora",
        "correo": "ana@example.com",
        "telefono": "+34 600 123 456",
        "password": "Password123",
    }
    base.update(overrides)
    return CrearUsuarioDTO(**base)


@pytest.mark.integration
class TestCrearUsuario:
    """RF-16: alta de gestión con contraseña utilizable."""

    def test_crear_usuario_persiste_hash_y_permite_login(self, usuario_service, auth_service):
        """RF-16: el usuario creado inicia sesión con la contraseña indicada."""
        creado = usuario_service.crear_usuario(_datos())

        assert isinstance(creado.id, UUID)
        assert creado.nombre == "Ana Gestora"
        assert creado.correo == "ana@example.com"
        assert creado.telefono == "+34 600 123 456"
        assert creado.roles == [RolUsuario.ESTUDIANTE]  # default del DTO
        assert creado.estado is True
        assert not hasattr(creado, "password_hash")

        login = auth_service.login(LoginDTO(correo="ana@example.com", password="Password123"))

        assert login.usuario.id == creado.id
        assert len(login.token) > 0

    def test_crear_usuario_roles_explicitos(self, usuario_service, auth_service):
        """RF-16: los roles del DTO se respetan en el alta."""
        creado = usuario_service.crear_usuario(_datos(roles=[RolUsuario.GESTOR_ALMACEN]))

        assert creado.roles == [RolUsuario.GESTOR_ALMACEN]

        login = auth_service.login(LoginDTO(correo="ana@example.com", password="Password123"))

        assert login.usuario.roles == [RolUsuario.GESTOR_ALMACEN]

    def test_crear_usuario_correo_duplicado_409(self, usuario_service):
        """RF-16: correo repetido lanza 409 y no duplica el usuario."""
        usuario_service.crear_usuario(_datos())

        with pytest.raises(HTTPException) as exc:
            usuario_service.crear_usuario(_datos(nombre="Otra Persona"))

        assert exc.value.status_code == 409
        assert exc.value.detail == "Correo ya registrado"
        assert len(usuario_service.listar_usuarios()) == 1

    def test_crear_usuario_password_debil_no_se_crea(self, usuario_service):
        """RF-16: contraseña que no cumple la complejidad no llega a crear el usuario."""
        with pytest.raises(ValidationError):
            _datos(password="debil")

        assert usuario_service.listar_usuarios() == []

    def test_crear_usuario_gestor_asigna_rol_solicitante_ok(self, usuario_service):
        """RF-09: Un gestor de almacén puede crear usuarios con rol solicitante."""
        actor_gestor = UsuarioDTO(
            id=uuid4(),
            nombre="Gestor",
            correo="gestor@example.com",
            telefono=None,
            roles=[RolUsuario.GESTOR_ALMACEN],
            estado=True,
        )
        creado = usuario_service.crear_usuario(
            _datos(roles=[RolUsuario.DOCENTE]), actor=actor_gestor
        )
        assert creado.roles == [RolUsuario.DOCENTE]

    def test_crear_usuario_gestor_asigna_rol_gestion_403(self, usuario_service):
        """RF-09: Un gestor de almacén no puede crear cuentas con rol de gestión."""
        actor_gestor = UsuarioDTO(
            id=uuid4(),
            nombre="Gestor",
            correo="gestor@example.com",
            telefono=None,
            roles=[RolUsuario.GESTOR_ALMACEN],
            estado=True,
        )
        with pytest.raises(HTTPException) as exc:
            usuario_service.crear_usuario(
                _datos(roles=[RolUsuario.GESTOR_ALMACEN]), actor=actor_gestor
            )
        assert exc.value.status_code == 403
        assert exc.value.detail == "El gestor de almacén solo puede asignar roles solicitantes"

        with pytest.raises(HTTPException) as exc2:
            usuario_service.crear_usuario(
                _datos(correo="admin2@example.com", roles=[RolUsuario.ADMINISTRADOR_SISTEMA]),
                actor=actor_gestor,
            )
        assert exc2.value.status_code == 403
        assert exc2.value.detail == "El gestor de almacén solo puede asignar roles solicitantes"

    def test_crear_usuario_admin_asigna_rol_gestion_ok(self, usuario_service):
        """RF-09: Un administrador de sistema sí puede crear cuentas con rol de gestión."""
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )
        creado = usuario_service.crear_usuario(
            _datos(roles=[RolUsuario.GESTOR_ALMACEN]), actor=actor_admin
        )
        assert creado.roles == [RolUsuario.GESTOR_ALMACEN]



@pytest.mark.integration
class TestListarUsuarios:
    """RF-17: listado de usuarios."""

    def test_listar_usuarios_devuelve_los_creados(self, usuario_service):
        """RF-17: el listado devuelve los usuarios creados como UsuarioDTO."""
        primero = usuario_service.crear_usuario(_datos())
        segundo = usuario_service.crear_usuario(
            _datos(nombre="Luis Docente", correo="luis@example.com")
        )

        listados = usuario_service.listar_usuarios()

        assert {u.id for u in listados} == {primero.id, segundo.id}
        assert all(isinstance(u, UsuarioDTO) for u in listados)


@pytest.mark.integration
class TestCambiarRolUsuario:
    """RF-10: cambio de rol de usuario."""

    def test_cambiar_rol_usuario_exito(self, usuario_service):
        creado = usuario_service.crear_usuario(_datos())
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )

        actualizado = usuario_service.cambiar_rol_usuario(
            id_usuario=creado.id, nuevo_rol=RolUsuario.DOCENTE, actor=actor_admin
        )
        assert actualizado.roles == [RolUsuario.DOCENTE]

    def test_cambiar_rol_usuario_inexistente_404(self, usuario_service):
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )
        with pytest.raises(HTTPException) as exc:
            usuario_service.cambiar_rol_usuario(
                id_usuario=uuid4(), nuevo_rol=RolUsuario.DOCENTE, actor=actor_admin
            )
        assert exc.value.status_code == 404
        assert exc.value.detail == "Usuario no encontrado"

    def test_cambiar_rol_usuario_autoproteccion_admin_409(self, usuario_service):
        admin_creado = usuario_service.crear_usuario(
            _datos(roles=[RolUsuario.ADMINISTRADOR_SISTEMA])
        )
        actor_admin = admin_creado

        with pytest.raises(HTTPException) as exc:
            usuario_service.cambiar_rol_usuario(
                id_usuario=admin_creado.id, nuevo_rol=RolUsuario.ESTUDIANTE, actor=actor_admin
            )
        assert exc.value.status_code == 409
        assert exc.value.detail == "No puedes quitarte el rol de administrador a ti mismo"


@pytest.mark.integration
class TestCambiarEstadoUsuario:
    """RF-11: activación y desactivación de usuarios."""

    def test_cambiar_estado_usuario_desactivar_y_reactivar(self, usuario_service):
        creado = usuario_service.crear_usuario(_datos())
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )

        desactivado = usuario_service.cambiar_estado_usuario(
            id_usuario=creado.id, estado=False, actor=actor_admin
        )
        assert desactivado.estado is False

        reactivado = usuario_service.cambiar_estado_usuario(
            id_usuario=creado.id, estado=True, actor=actor_admin
        )
        assert reactivado.estado is True

    def test_cambiar_estado_usuario_inexistente_404(self, usuario_service):
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )
        with pytest.raises(HTTPException) as exc:
            usuario_service.cambiar_estado_usuario(
                id_usuario=uuid4(), estado=False, actor=actor_admin
            )
        assert exc.value.status_code == 404
        assert exc.value.detail == "Usuario no encontrado"

    def test_cambiar_estado_usuario_autoproteccion_409(self, usuario_service):
        admin_creado = usuario_service.crear_usuario(
            _datos(roles=[RolUsuario.ADMINISTRADOR_SISTEMA])
        )
        actor_admin = admin_creado

        with pytest.raises(HTTPException) as exc:
            usuario_service.cambiar_estado_usuario(
                id_usuario=admin_creado.id, estado=False, actor=actor_admin
            )
        assert exc.value.status_code == 409
        assert exc.value.detail == "No puedes desactivar tu propia cuenta"


@pytest.mark.integration
class TestEliminarUsuario:
    """RF-12: eliminación segura de usuarios."""

    def test_eliminar_usuario_sin_operaciones_exito(self, usuario_service, usuario_repo):
        creado = usuario_service.crear_usuario(_datos())
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )

        usuario_service.eliminar_usuario(creado.id, actor=actor_admin)
        assert usuario_repo.obtener_por_id(creado.id) is None

    def test_eliminar_usuario_inexistente_404(self, usuario_service):
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )
        with pytest.raises(HTTPException) as exc:
            usuario_service.eliminar_usuario(uuid4(), actor=actor_admin)
        assert exc.value.status_code == 404
        assert exc.value.detail == "Usuario no encontrado"

    def test_eliminar_usuario_autoproteccion_409(self, usuario_service):
        admin_creado = usuario_service.crear_usuario(
            _datos(roles=[RolUsuario.ADMINISTRADOR_SISTEMA])
        )
        actor_admin = admin_creado

        with pytest.raises(HTTPException) as exc:
            usuario_service.eliminar_usuario(admin_creado.id, actor=actor_admin)
        assert exc.value.status_code == 409
        assert exc.value.detail == "No puedes eliminar tu propia cuenta"

    def test_eliminar_usuario_con_reservas_activas_409(self, usuario_repo):
        mock_reservas = MagicMock()
        mock_reservas.contar_reservas_activas_usuario.return_value = 1
        service = UsuarioService(usuario_repo, reserva_service=mock_reservas)

        creado = service.crear_usuario(_datos())
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )

        with pytest.raises(HTTPException) as exc:
            service.eliminar_usuario(creado.id, actor=actor_admin)
        assert exc.value.status_code == 409
        assert exc.value.detail == "No se puede eliminar un usuario con reservas activas o préstamos en curso"

    def test_eliminar_usuario_con_prestamos_en_curso_409(self, usuario_repo):
        mock_prestamos = MagicMock()
        mock_prestamos.contar_prestamos_en_curso.return_value = 1
        service = UsuarioService(usuario_repo, prestamo_service=mock_prestamos)

        creado = service.crear_usuario(_datos())
        actor_admin = UsuarioDTO(
            id=uuid4(),
            nombre="Admin",
            correo="admin@example.com",
            telefono=None,
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
            estado=True,
        )

        with pytest.raises(HTTPException) as exc:
            service.eliminar_usuario(creado.id, actor=actor_admin)
        assert exc.value.status_code == 409
        assert exc.value.detail == "No se puede eliminar un usuario con reservas activas o préstamos en curso"

