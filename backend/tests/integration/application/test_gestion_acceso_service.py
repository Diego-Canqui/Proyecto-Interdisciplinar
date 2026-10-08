"""Tests de integración para GestionAccesoService (application + DB)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from prestamos_recursos.config import settings
from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import (
    AutenticacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.gestion_acceso_service import (
    GestionAccesoService,
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
def auth_service(usuario_repo):
    return AutenticacionService(usuario_repo)


@pytest.fixture
def gestion_acceso_service(auth_service):
    return GestionAccesoService(auth_service)


@pytest.mark.integration
class TestAutenticarJWT:
    """Tests para autenticar_jwt (RF-10, RF-11)."""

    def test_autenticar_jwt_token_valido_retorna_true(self, gestion_acceso_service, auth_service):
        """RF-10: autenticar_jwt retorna True con token válido."""
        # Registrar usuario y obtener token
        datos_registro = CrearUsuarioDTO(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )
        resultado = auth_service.registrar_usuario(datos_registro)
        token = resultado.token

        # Token válido debe retornar True
        assert gestion_acceso_service.autenticar_jwt(token) is True

    def test_autenticar_jwt_token_invalido_retorna_false(self, gestion_acceso_service):
        """RF-11: autenticar_jwt retorna False con token inválido/mal formado."""
        # Token mal formado
        assert gestion_acceso_service.autenticar_jwt("token.invalido") is False

        # Token con firma incorrecta
        payload_falso = {"sub": "00000000-0000-0000-0000-000000000000", "roles": ["ESTUDIANTE"]}
        token_falso = jwt.encode(payload_falso, "otro-secret", algorithm="HS256")
        assert gestion_acceso_service.autenticar_jwt(token_falso) is False

    def test_autenticar_jwt_token_expirado_retorna_false(self, gestion_acceso_service):
        """RF-11: autenticar_jwt retorna False con token expirado."""
        # Token expirado
        payload = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "roles": ["ESTUDIANTE"],
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }
        token_expirado = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        assert gestion_acceso_service.autenticar_jwt(token_expirado) is False


@pytest.mark.integration
class TestObtenerUsuarioAutenticado:
    """Tests para obtener_usuario_autenticado (RF-10, RF-11)."""

    def test_obtener_usuario_autenticado_extrae_sub_y_busca_usuario(
        self, gestion_acceso_service, auth_service
    ):
        """RF-10: obtener_usuario_autenticado extrae sub del JWT y busca usuario."""
        # Registrar usuario y obtener token
        datos_registro = CrearUsuarioDTO(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )
        resultado = auth_service.registrar_usuario(datos_registro)
        token = resultado.token

        # Obtener usuario autenticado
        usuario_dto = gestion_acceso_service.obtener_usuario_autenticado(token)

        assert usuario_dto is not None
        assert isinstance(usuario_dto, UsuarioDTO)
        assert usuario_dto.id == resultado.usuario.id
        assert usuario_dto.nombre == "Juan Pérez"
        assert usuario_dto.correo == "juan@example.com"
        assert usuario_dto.telefono == "+34 600 123 456"
        assert usuario_dto.roles == [RolUsuario.ESTUDIANTE]
        assert usuario_dto.estado is True

    def test_obtener_usuario_autenticado_token_invalido_retorna_none(
        self, gestion_acceso_service
    ):
        """RF-11: obtener_usuario_autenticado con token inválido retorna None."""
        assert gestion_acceso_service.obtener_usuario_autenticado("token.invalido") is None

    def test_obtener_usuario_autenticado_token_expirado_retorna_none(
        self, gestion_acceso_service
    ):
        """RF-11: obtener_usuario_autenticado con token expirado retorna None."""
        payload = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "roles": ["ESTUDIANTE"],
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }
        token_expirado = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        assert gestion_acceso_service.obtener_usuario_autenticado(token_expirado) is None

    def test_obtener_usuario_autenticado_usuario_inexistente_retorna_none(
        self, gestion_acceso_service
    ):
        """RF-11: obtener_usuario_autenticado con token válido pero usuario borrado retorna None."""
        payload = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "roles": ["ESTUDIANTE"],
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        assert gestion_acceso_service.obtener_usuario_autenticado(token) is None


@pytest.mark.integration
class TestVerificarPermisos:
    """Tests para verificar_permisos (RF-10)."""

    def test_verificar_permisos_usuario_tiene_rol_retorna_true(
        self, gestion_acceso_service, auth_service
    ):
        """verificar_permisos retorna True si usuario tiene el rol solicitado."""
        # Registrar usuario con rol ADMINISTRADOR_SISTEMA
        datos_registro = CrearUsuarioDTO(
            nombre="Admin User",
            correo="admin@example.com",
            telefono="+34 600 123 456",
            password="Password123",
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
        )
        resultado = auth_service.registrar_usuario(datos_registro)
        usuario_id = resultado.usuario.id

        # Verificar que tiene el rol
        assert (
            gestion_acceso_service.verificar_permisos(usuario_id, RolUsuario.ADMINISTRADOR_SISTEMA)
            is True
        )

    def test_verificar_permisos_usuario_no_tiene_rol_retorna_false(
        self, gestion_acceso_service, auth_service
    ):
        """verificar_permisos retorna False si usuario NO tiene el rol solicitado."""
        # Registrar usuario con rol ESTUDIANTE (por defecto)
        datos_registro = CrearUsuarioDTO(
            nombre="Estudiante User",
            correo="estudiante@example.com",
            telefono="+34 600 123 456",
            password="Password123",
        )
        resultado = auth_service.registrar_usuario(datos_registro)
        usuario_id = resultado.usuario.id

        # Verificar que NO tiene rol ADMINISTRADOR_SISTEMA
        assert (
            gestion_acceso_service.verificar_permisos(usuario_id, RolUsuario.ADMINISTRADOR_SISTEMA)
            is False
        )

    def test_verificar_permisos_usuario_con_multiples_roles(
        self, gestion_acceso_service, auth_service
    ):
        """verificar_permisos funciona con usuario que tiene múltiples roles."""
        datos_registro = CrearUsuarioDTO(
            nombre="Multi Role User",
            correo="multi@example.com",
            telefono="+34 600 123 456",
            password="Password123",
            roles=[RolUsuario.DOCENTE, RolUsuario.GESTOR_ALMACEN],
        )
        resultado = auth_service.registrar_usuario(datos_registro)
        usuario_id = resultado.usuario.id

        assert (
            gestion_acceso_service.verificar_permisos(usuario_id, RolUsuario.DOCENTE) is True
        )
        assert (
            gestion_acceso_service.verificar_permisos(usuario_id, RolUsuario.GESTOR_ALMACEN) is True
        )
        assert (
            gestion_acceso_service.verificar_permisos(usuario_id, RolUsuario.ADMINISTRADOR_SISTEMA)
            is False
        )

    def test_verificar_permisos_usuario_inexistente_retorna_false(
        self, gestion_acceso_service
    ):
        """verificar_permisos retorna False para usuario inexistente."""
        usuario_inexistente = "00000000-0000-0000-0000-000000000000"
        assert (
            gestion_acceso_service.verificar_permisos(usuario_inexistente, RolUsuario.ESTUDIANTE)
            is False
        )