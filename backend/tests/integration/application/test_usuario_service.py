"""Tests de integración para UsuarioService (application + DB)."""
from __future__ import annotations

from uuid import UUID

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
