"""Tests de integración para ReputacionService (application + DB)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import (
    AutenticacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import (
    ExcepcionAcademicaDTO,
    PerfilReputacionDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.reputacion_service import (
    ReputacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_excepcion_academica_repository import (
    SqlExcepcionAcademicaRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_perfil_reputacion_repository import (
    SqlPerfilReputacionRepository,
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


@pytest.fixture
def perfil_repo(db_session):
    return SqlPerfilReputacionRepository(db_session)


@pytest.fixture
def excepcion_repo(db_session):
    return SqlExcepcionAcademicaRepository(db_session)


@pytest.fixture
def auth_service(usuario_repo):
    return AutenticacionService(usuario_repo)


@pytest.fixture
def reputacion_service(perfil_repo, excepcion_repo):
    return ReputacionService(perfil_repo, excepcion_repo)


@pytest.fixture
def usuario_creado(auth_service):
    """Crea un usuario de prueba y retorna su ID."""
    datos = CrearUsuarioDTO(
        nombre="Juan Pérez",
        correo="juan@example.com",
        telefono="+34 600 123 456",
        password="Password123",
    )
    resultado = auth_service.registrar_usuario(datos)
    return resultado.usuario.id


@pytest.mark.integration
class TestObtenerPerfil:
    """Tests para obtener_perfil."""

    def test_obtener_perfil_crea_si_no_existe(self, reputacion_service, usuario_creado):
        """RF-18: obtener_perfil crea perfil si no existe (factory) y lo devuelve como DTO."""
        perfil_dto = reputacion_service.obtener_perfil(usuario_creado)

        assert isinstance(perfil_dto, PerfilReputacionDTO)
        assert perfil_dto.usuario_id == usuario_creado
        assert perfil_dto.puntaje == 500  # Puntaje inicial por factory
        assert perfil_dto.nivel == NivelReputacion.NORMAL
        assert isinstance(perfil_dto.fecha_actualizacion, datetime)
        assert perfil_dto.sanciones == []

    def test_obtener_perfil_retorna_existente(self, reputacion_service, perfil_repo, usuario_creado):
        """Si el perfil ya existe, lo retorna sin crear uno nuevo."""
        # Primera llamada crea el perfil
        perfil_dto_1 = reputacion_service.obtener_perfil(usuario_creado)
        perfil_id = perfil_dto_1.id

        # Segunda llamada debe retornar el mismo perfil
        perfil_dto_2 = reputacion_service.obtener_perfil(usuario_creado)

        assert perfil_dto_2.id == perfil_id
        assert perfil_dto_2.usuario_id == usuario_creado
        assert perfil_dto_2.puntaje == 500


@pytest.mark.integration
class TestEsElegibleParaPrestamo:
    """Tests para es_elegible_para_prestamo."""

    def test_es_elegible_perfil_nuevo_sin_sanciones(self, reputacion_service, usuario_creado):
        """Perfil nuevo (NORMAL, sin sanciones) es elegible."""
        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is True

    def test_es_elegible_nivel_bajo_no_elegible(self, reputacion_service, perfil_repo, usuario_creado):
        """Nivel BAJO -> no elegible."""
        # Obtener perfil y bajar puntaje manualmente
        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        perfil.puntaje = perfil.puntaje.restar(300)  # 500 - 300 = 200 -> BAJO
        perfil.recalcular_nivel()
        perfil_repo.guardar(perfil)

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is False

    def test_es_elegible_sancion_activa_bloqueante(self, reputacion_service, usuario_creado):
        """Sanción activa sin excepción -> no elegible."""
        # Aplicar sanción TARDANZA
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Devolución tardía")

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is False

    def test_es_elegible_excepcion_vigente_cubre_tardanza(self, reputacion_service, excepcion_repo, usuario_creado):
        """Excepción vigente cubre TARDANZA -> elegible."""
        # Aplicar sanción TARDANZA
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Devolución tardía")

        # Registrar excepción vigente
        ahora = datetime.now(UTC)
        inicio = ahora - timedelta(days=1)
        fin = ahora + timedelta(days=1)
        reputacion_service.registrar_excepcion(usuario_creado, "Examen final", inicio, fin)

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is True

    def test_es_elegible_excepcion_no_vigente_no_cubre(self, reputacion_service, excepcion_repo, usuario_creado):
        """Excepción no vigente (fecha pasada) no cubre TARDANZA -> no elegible."""
        # Aplicar sanción TARDANZA
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Devolución tardía")

        # Registrar excepción expirada
        ahora = datetime.now(UTC)
        inicio = ahora - timedelta(days=10)
        fin = ahora - timedelta(days=5)
        reputacion_service.registrar_excepcion(usuario_creado, "Examen final", inicio, fin)

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is False

    def test_es_elegible_excepcion_cubre_inasistencia_reserva(self, reputacion_service, excepcion_repo, usuario_creado):
        """Excepción vigente cubre INASISTENCIA_RESERVA -> elegible."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.INASISTENCIA_RESERVA, "No asistió a reserva")

        ahora = datetime.now(UTC)
        inicio = ahora - timedelta(days=1)
        fin = ahora + timedelta(days=1)
        reputacion_service.registrar_excepcion(usuario_creado, "Enfermedad", inicio, fin)

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is True

    def test_es_elegible_excepcion_no_cubre_dano_parcial(self, reputacion_service, excepcion_repo, usuario_creado):
        """Excepción NO cubre DANO_PARCIAL -> no elegible aunque haya excepción vigente."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.DANO_PARCIAL, "Dañó recurso")

        ahora = datetime.now(UTC)
        inicio = ahora - timedelta(days=1)
        fin = ahora + timedelta(days=1)
        reputacion_service.registrar_excepcion(usuario_creado, "Examen final", inicio, fin)

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is False


@pytest.mark.integration
class TestAplicarSancion:
    """Tests para aplicar_sancion."""

    def test_aplicar_sancion_tardanza_actualiza_perfil(self, reputacion_service, perfil_repo, usuario_creado):
        """RF-20: aplicar_sancion crea Sancion con descuentos según TipoSancion, actualiza perfil, persiste."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Devolución tardía de 3 días")

        # Verificar perfil actualizado
        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil is not None
        assert len(perfil.sanciones) == 1
        sancion = perfil.sanciones[0]
        assert sancion.tipo == TipoSancion.TARDANZA
        assert sancion.puntos_descuento == -10
        assert sancion.monto_descuento == Decimal(0)
        assert sancion.motivo == "Devolución tardía de 3 días"
        assert sancion.activa is True
        # Puntaje: 500 - 10 = 490 (sigue siendo NORMAL)
        assert perfil.puntaje.puntos == 490
        assert perfil.nivel == NivelReputacion.NORMAL

    def test_aplicar_sancion_dano_parcial(self, reputacion_service, perfil_repo, usuario_creado):
        """DANO_PARCIAL: -30 pts, $50."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.DANO_PARCIAL, "Rayó la pantalla")

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        sancion = perfil.sanciones[0]
        assert sancion.tipo == TipoSancion.DANO_PARCIAL
        assert sancion.puntos_descuento == -30
        assert sancion.monto_descuento == Decimal(50)
        assert perfil.puntaje.puntos == 470

    def test_aplicar_sancion_dano_total(self, reputacion_service, perfil_repo, usuario_creado):
        """DANO_TOTAL: -100 pts, monto 0 (se calcula en service según valor recurso)."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.DANO_TOTAL, "Rompe recurso completamente")

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        sancion = perfil.sanciones[0]
        assert sancion.tipo == TipoSancion.DANO_TOTAL
        assert sancion.puntos_descuento == -100
        assert sancion.monto_descuento == Decimal(0)
        assert perfil.puntaje.puntos == 400

    def test_aplicar_sancion_inasistencia_reserva(self, reputacion_service, perfil_repo, usuario_creado):
        """INASISTENCIA_RESERVA: -15 pts, $0."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.INASISTENCIA_RESERVA, "No vino a recoger")

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        sancion = perfil.sanciones[0]
        assert sancion.tipo == TipoSancion.INASISTENCIA_RESERVA
        assert sancion.puntos_descuento == -15
        assert sancion.monto_descuento == Decimal(0)
        assert perfil.puntaje.puntos == 485

    def test_aplicar_sancion_multiples_acumula_y_recalcula(self, reputacion_service, perfil_repo, usuario_creado):
        """Múltiples sanciones se acumulan y recalculan nivel."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Tardanza 1")
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.DANO_PARCIAL, "Daño")
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.INASISTENCIA_RESERVA, "No asistió")

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert len(perfil.sanciones) == 3
        # 500 - 10 - 30 - 15 = 445
        assert perfil.puntaje.puntos == 445
        assert perfil.nivel == NivelReputacion.NORMAL

    def test_aplicar_sancion_lleva_a_nivel_bajo(self, reputacion_service, perfil_repo, usuario_creado):
        """Sanciones suficientes llevan a nivel BAJO."""
        # Aplicar muchas sanciones para bajar a BAJO (< 300)
        for i in range(15):  # 15 * -10 = -150 -> 350, aún NORMAL
            reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, f"Tardanza {i}")

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil.puntaje.puntos == 350  # 500 - 150
        assert perfil.nivel == NivelReputacion.NORMAL

        # Una más para bajar a BAJO
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.DANO_PARCIAL, "Daño grande")
        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil.puntaje.puntos == 320  # 350 - 30
        assert perfil.nivel == NivelReputacion.NORMAL

        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.DANO_PARCIAL, "Otro daño")
        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil.puntaje.puntos == 290  # 320 - 30
        assert perfil.nivel == NivelReputacion.BAJO


@pytest.mark.integration
class TestRegistrarExcepcion:
    """Tests para registrar_excepcion."""

    def test_registrar_excepcion_persiste_y_devuelve_dto(self, reputacion_service, excepcion_repo, usuario_creado):
        """RF-21: registrar_excepcion crea ExcepcionAcademica, persiste, devuelve DTO."""
        ahora = datetime.now(UTC)
        inicio = ahora + timedelta(days=1)
        fin = ahora + timedelta(days=10)

        excepcion_dto = reputacion_service.registrar_excepcion(
            usuario_creado, "Examen final de programación", inicio, fin
        )

        assert isinstance(excepcion_dto, ExcepcionAcademicaDTO)
        assert excepcion_dto.usuario_id == usuario_creado
        assert excepcion_dto.motivo == "Examen final de programación"
        assert excepcion_dto.fecha_inicio == inicio
        assert excepcion_dto.fecha_fin == fin
        assert excepcion_dto.activa is True

        # Verificar en BD
        excepcion_bd = excepcion_repo.obtener_por_id(excepcion_dto.id)
        assert excepcion_bd is not None
        assert excepcion_bd.motivo == "Examen final de programación"
        assert excepcion_bd.activa is True

    def test_registrar_excepcion_fecha_inicio_pasada_vigente_desde_ahora(self, reputacion_service, usuario_creado):
        """Si fecha_inicio es pasada, la excepción es vigente desde ahora."""
        ahora = datetime.now(UTC)
        inicio = ahora - timedelta(days=1)  # Ayer
        fin = ahora + timedelta(days=10)

        excepcion_dto = reputacion_service.registrar_excepcion(usuario_creado, "Motivo", inicio, fin)

        assert excepcion_dto.activa is True
        # Verificamos indirectamente via es_elegible_para_prestamo
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Tardanza")
        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is True