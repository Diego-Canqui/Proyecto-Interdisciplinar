"""Tests de integración para SqlUsuarioRepository (infrastructure + DB)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.excepcion_academica_model import (
    ExcepcionAcademicaModel,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import (
    PerfilReputacionModel,
    SancionModel,
)
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


@pytest.mark.integration
class TestSqlUsuarioRepository:
    """Tests para SqlUsuarioRepository."""

    def test_guardar_y_obtener_por_id(self, usuario_repo):
        """RF-01: Guardar usuario y obtenerlo por ID."""
        usuario = Usuario.crear_con_password(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password_plano="Password123",
        )

        guardado = usuario_repo.guardar(usuario)

        # El método guardar debe retornar la entidad con ID
        assert guardado is not None
        assert isinstance(guardado.id, UUID)
        assert guardado.nombre == "Juan Pérez"
        assert guardado.correo == "juan@example.com"
        assert guardado.telefono == "+34 600 123 456"
        assert guardado.password_hash == usuario.password_hash
        assert guardado.roles == [RolUsuario.ESTUDIANTE]
        assert guardado.estado is True

        # Obtener por ID
        obtenido = usuario_repo.obtener_por_id(guardado.id)
        assert obtenido is not None
        assert obtenido.id == guardado.id
        assert obtenido.nombre == "Juan Pérez"
        assert obtenido.correo == "juan@example.com"
        assert obtenido.password_hash == usuario.password_hash

    def test_obtener_por_correo_existente(self, usuario_repo):
        """RF-01: Obtener usuario por correo existente."""
        usuario = Usuario.crear_con_password(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password_plano="Password123",
        )
        usuario_repo.guardar(usuario)

        obtenido = usuario_repo.obtener_por_correo("juan@example.com")

        assert obtenido is not None
        assert obtenido.correo == "juan@example.com"
        assert obtenido.nombre == "Juan Pérez"

    def test_obtener_por_correo_inexistente_retorna_none(self, usuario_repo):
        """RF-01: Obtener por correo inexistente retorna None."""
        obtenido = usuario_repo.obtener_por_correo("noexiste@example.com")
        assert obtenido is None

    def test_guardar_correo_duplicado_lanza_excepcion(self, usuario_repo):
        """RF-02: Guardar usuario con correo duplicado lanza IntegrityError (constraint UNIQUE)."""
        usuario1 = Usuario.crear_con_password(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password_plano="Password123",
        )
        usuario_repo.guardar(usuario1)

        usuario2 = Usuario.crear_con_password(
            nombre="Otro Usuario",
            correo="juan@example.com",  # Mismo correo
            telefono="+34 600 999 999",
            password_plano="OtroPass123",
        )

        with pytest.raises(IntegrityError):
            usuario_repo.guardar(usuario2)

    def test_listar_retorna_todos(self, usuario_repo):
        """RF-10: Listar retorna todos los usuarios."""
        usuario1 = Usuario.crear_con_password(
            nombre="Usuario 1",
            correo="user1@example.com",
            telefono=None,
            password_plano="Password123",
        )
        usuario2 = Usuario.crear_con_password(
            nombre="Usuario 2",
            correo="user2@example.com",
            telefono="+34 600 111 111",
            password_plano="Password123",
            roles=[RolUsuario.DOCENTE],
        )
        usuario_repo.guardar(usuario1)
        usuario_repo.guardar(usuario2)

        usuarios = usuario_repo.listar()

        assert len(usuarios) == 2
        correos = {u.correo for u in usuarios}
        assert correos == {"user1@example.com", "user2@example.com"}

    def test_guardar_persiste_password_hash_y_roles(self, usuario_repo):
        """RF-07, RF-08: Guardar persiste password_hash y roles correctamente."""
        usuario = Usuario.crear_con_password(
            nombre="Test User",
            correo="test@example.com",
            telefono=None,
            password_plano="MySecretPass123",
            roles=[RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN],
        )
        guardado = usuario_repo.guardar(usuario)

        # Verificar que el hash se persiste (no el password plano)
        assert guardado.password_hash is not None
        assert guardado.password_hash != "MySecretPass123"
        assert guardado.password_hash.startswith("$2b$12$")

        # Verificar que los roles se persisten como strings
        assert guardado.roles == [RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN]

        # Verificar que se puede verificar el password
        assert guardado.verificar_password("MySecretPass123") is True
        assert guardado.verificar_password("WrongPass") is False

    def test_eliminar_usuario_existente_retorna_true(self, usuario_repo):
        """RF-12: eliminar borra el usuario existente y retorna True."""
        usuario = Usuario.crear_con_password(
            nombre="Para Eliminar",
            correo="eliminar@example.com",
            telefono=None,
            password_plano="Password123",
        )
        guardado = usuario_repo.guardar(usuario)
        assert usuario_repo.obtener_por_id(guardado.id) is not None

        resultado = usuario_repo.eliminar(guardado.id)
        assert resultado is True
        assert usuario_repo.obtener_por_id(guardado.id) is None

    def test_eliminar_usuario_inexistente_retorna_false(self, usuario_repo):
        """RF-12: eliminar usuario inexistente retorna False."""
        resultado = usuario_repo.eliminar(uuid4())
        assert resultado is False

    def test_eliminar_usuario_limpia_perfil_sanciones_y_excepciones(self, db_session, usuario_repo):
        """RF-12: eliminar usuario borra también su perfil, sanciones y excepciones académicas."""
        usuario = Usuario.crear_con_password(
            nombre="Con Dependencias",
            correo="deps@example.com",
            telefono=None,
            password_plano="Password123",
        )
        guardado = usuario_repo.guardar(usuario)

        # Crear perfil con sanción
        ahora = datetime.now(UTC)
        perfil = PerfilReputacionModel(
            id=uuid4(),
            usuario_id=guardado.id,
            puntos=450,
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=ahora,
        )
        db_session.add(perfil)
        db_session.flush()

        sancion = SancionModel(
            id=uuid4(),
            perfil_reputacion_id=perfil.id,
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=50,
            monto_descuento=Decimal(0),
            motivo="Devolución tardía",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=3),
            activa=True,
        )
        db_session.add(sancion)

        # Crear excepción académica
        excepcion = ExcepcionAcademicaModel(
            id=uuid4(),
            usuario_id=guardado.id,
            motivo="Justificación médica",
            fecha_inicio=ahora,
            fecha_fin=ahora + timedelta(days=7),
            activa=True,
        )
        db_session.add(excepcion)
        db_session.flush()

        # Eliminar usuario
        resultado = usuario_repo.eliminar(guardado.id)
        assert resultado is True

        # Comprobar que usuario no existe
        assert usuario_repo.obtener_por_id(guardado.id) is None

        # Comprobar que perfil, sanción y excepción ya no existen
        perfil_restante = db_session.scalar(
            select(PerfilReputacionModel).where(PerfilReputacionModel.usuario_id == guardado.id)
        )
        assert perfil_restante is None

        sanciones_restantes = db_session.scalars(
            select(SancionModel).where(SancionModel.perfil_reputacion_id == perfil.id)
        ).all()
        assert len(sanciones_restantes) == 0

        excepciones_restantes = db_session.scalars(
            select(ExcepcionAcademicaModel).where(ExcepcionAcademicaModel.usuario_id == guardado.id)
        ).all()
        assert len(excepciones_restantes) == 0
