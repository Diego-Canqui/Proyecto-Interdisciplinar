"""Tests de integración para ReputacionService (application + DB)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import (
    AutenticacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import (
    ElegibilidadDTO,
    ExcepcionAcademicaDTO,
    PerfilGestionDTO,
    PerfilReputacionDTO,
    SancionDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.excepciones import (
    ExcepcionNoEncontrada,
    SancionInvalida,
    UsuarioNoEncontrado,
)
from prestamos_recursos.contexts.identidad_reputacion.application.reputacion_service import (
    ReputacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import (
    PerfilReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.estado_excepcion import (
    EstadoExcepcion,
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
def reputacion_service(perfil_repo, excepcion_repo, usuario_repo):
    return ReputacionService(perfil_repo, excepcion_repo, usuario_repo)


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
        """RF-01: el nivel BAJO NO bloquea el préstamo (deroga la RF-19 de la spec 001) -> elegible."""
        # Crear el perfil (500, NORMAL) y bajar el puntaje manualmente
        reputacion_service.obtener_perfil(usuario_creado)
        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        perfil.puntaje = perfil.puntaje.restar(300)  # 500 - 300 = 200 -> BAJO
        perfil.recalcular_nivel()
        perfil_repo.guardar(perfil)
        assert perfil.nivel == NivelReputacion.BAJO

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is True

    def test_es_elegible_sancion_activa_bloqueante(self, reputacion_service, usuario_creado):
        """Sanción activa sin excepción -> no elegible."""
        # Aplicar sanción TARDANZA
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Devolución tardía", dias_retardo=3)

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is False

    def test_es_elegible_excepcion_vigente_cubre_tardanza(self, reputacion_service, excepcion_repo, usuario_creado):
        """Excepción vigente cubre TARDANZA -> elegible."""
        # Aplicar sanción TARDANZA
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Devolución tardía", dias_retardo=3)

        # Registrar excepción vigente
        ahora = datetime.now(UTC)
        inicio = ahora - timedelta(days=1)
        fin = ahora + timedelta(days=1)
        reputacion_service.registrar_excepcion(usuario_creado, "Examen final", inicio, fin)

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is True

    def test_es_elegible_excepcion_no_vigente_no_cubre(self, reputacion_service, excepcion_repo, usuario_creado):
        """Excepción no vigente (fecha pasada) no cubre TARDANZA -> no elegible."""
        # Aplicar sanción TARDANZA
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Devolución tardía", dias_retardo=3)

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
        """RF-03/RF-08: aplicar_sancion crea Sancion con descuentos según TipoSancion, actualiza perfil, persiste."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Devolución tardía de 3 días", dias_retardo=3)

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
        # RF-05: retraso 3 días → 3 días de bloqueo desde la fecha de aplicación
        assert sancion.fecha_fin == sancion.fecha_aplicacion + timedelta(days=3)
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
        """DANO_TOTAL: -100 pts y la deuda es el valor del recurso (monto_opcional, RF-06)."""
        reputacion_service.aplicar_sancion(
            usuario_creado,
            TipoSancion.DANO_TOTAL,
            "Rompe recurso completamente",
            monto_opcional=Decimal("200.00"),
        )

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        sancion = perfil.sanciones[0]
        assert sancion.tipo == TipoSancion.DANO_TOTAL
        assert sancion.puntos_descuento == -100
        assert sancion.monto_descuento == Decimal("200.00")
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
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Tardanza 1", dias_retardo=3)
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
            reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, f"Tardanza {i}", dias_retardo=3)

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

    def test_aplicar_sancion_devuelve_dto_real_persistido(self, reputacion_service, perfil_repo, usuario_creado):
        """RF-08: retorna el SancionDTO de la sanción creada (id real y persistido)."""
        sancion_dto = reputacion_service.aplicar_sancion(
            usuario_creado, TipoSancion.DANO_PARCIAL, "Rayó la pantalla"
        )

        assert isinstance(sancion_dto, SancionDTO)
        assert isinstance(sancion_dto.id, UUID)

        # El id del DTO es el de la sanción realmente persistida
        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert [s.id for s in perfil.sanciones] == [sancion_dto.id]
        assert sancion_dto.monto_descuento == Decimal(50)
        assert sancion_dto.activa is True
        assert sancion_dto.vigente is True

    @pytest.mark.parametrize(
        ("tipo", "dias_retardo", "monto_opcional", "dias_bloqueo"),
        [
            (TipoSancion.TARDANZA, 1, None, 0),  # gracia: expira al aplicarse (D2)
            (TipoSancion.TARDANZA, 2, None, 2),
            (TipoSancion.INASISTENCIA_RESERVA, None, None, 3),
            (TipoSancion.DANO_PARCIAL, None, None, 30),
            (TipoSancion.DANO_TOTAL, None, Decimal("200.00"), 60),
        ],
    )
    def test_aplicar_sancion_deriva_fecha_fin_por_tipo(
        self,
        reputacion_service,
        usuario_creado,
        tipo,
        dias_retardo,
        monto_opcional,
        dias_bloqueo,
    ):
        """RF-03/RF-05: fecha_fin = fecha_aplicacion + duracion_bloqueo del tipo, y vigencia derivada."""
        sancion_dto = reputacion_service.aplicar_sancion(
            usuario_creado,
            tipo,
            "Motivo de prueba",
            monto_opcional=monto_opcional,
            dias_retardo=dias_retardo,
        )

        assert sancion_dto.tipo == tipo
        assert sancion_dto.fecha_fin == sancion_dto.fecha_aplicacion + timedelta(days=dias_bloqueo)
        # La gracia (0 días de bloqueo) no está vigente ni en su instante de creación
        assert sancion_dto.vigente is (dias_bloqueo > 0)

    def test_aplicar_sancion_ignora_monto_y_retraso_en_tipos_fijos(self, reputacion_service, usuario_creado):
        """RF-06/RF-07: los tipos de deuda y duración fija ignoran monto_opcional y dias_retardo."""
        sancion_dto = reputacion_service.aplicar_sancion(
            usuario_creado,
            TipoSancion.DANO_PARCIAL,
            "Daño con parámetros ajenos",
            monto_opcional=Decimal("999.00"),
            dias_retardo=7,
        )

        assert sancion_dto.monto_descuento == Decimal(50)  # deuda fija del tipo
        assert sancion_dto.fecha_fin == sancion_dto.fecha_aplicacion + timedelta(days=30)

    def test_aplicar_sancion_tardanza_sin_dias_retardo_lanza_sancion_invalida(
        self, reputacion_service, usuario_creado
    ):
        """RF-07: TARDANZA exige dias_retardo >= 1 (ausente, 0 o negativo) sin HTTP (D4/D5)."""
        with pytest.raises(SancionInvalida):
            reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Tardanza sin retraso")

        with pytest.raises(SancionInvalida):
            reputacion_service.aplicar_sancion(
                usuario_creado, TipoSancion.TARDANZA, "Retraso 0", dias_retardo=0
            )

        with pytest.raises(SancionInvalida):
            reputacion_service.aplicar_sancion(
                usuario_creado, TipoSancion.TARDANZA, "Retraso negativo", dias_retardo=-2
            )

    def test_aplicar_sancion_dano_total_sin_monto_lanza_sancion_invalida(
        self, reputacion_service, usuario_creado
    ):
        """RF-06: DANO_TOTAL exige monto > 0 (deuda $0 falsearía el registro) sin HTTP."""
        with pytest.raises(SancionInvalida):
            reputacion_service.aplicar_sancion(
                usuario_creado, TipoSancion.DANO_TOTAL, "Rompe recurso sin monto"
            )

        with pytest.raises(SancionInvalida):
            reputacion_service.aplicar_sancion(
                usuario_creado, TipoSancion.DANO_TOTAL, "Monto 0", monto_opcional=Decimal(0)
            )

        with pytest.raises(SancionInvalida):
            reputacion_service.aplicar_sancion(
                usuario_creado, TipoSancion.DANO_TOTAL, "Monto negativo", monto_opcional=Decimal(-5)
            )

    def test_aplicar_sancion_usuario_inexistente_lanza_usuario_no_encontrado(
        self, reputacion_service, perfil_repo
    ):
        """RF-23: un usuario_id no registrado se rechaza sin crear perfiles huérfanos."""
        usuario_fantasma = uuid4()

        with pytest.raises(UsuarioNoEncontrado):
            reputacion_service.aplicar_sancion(
                usuario_fantasma, TipoSancion.DANO_PARCIAL, "Daño de un usuario inexistente"
            )

        assert perfil_repo.obtener_por_usuario(usuario_fantasma) is None


@pytest.mark.integration
class TestExcepcionesDeAplicacion:
    """RF-23 (D4): excepciones propias del servicio, sin HTTP, capturables por otros contextos."""

    def test_excepciones_de_aplicacion_no_son_http(self):
        """Las excepciones de `application/excepciones.py` no dependen de FastAPI."""
        for excepcion in (ExcepcionNoEncontrada, SancionInvalida, UsuarioNoEncontrado):
            assert issubclass(excepcion, Exception)
            assert not issubclass(excepcion, HTTPException)


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
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Tardanza", dias_retardo=3)
        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is True

    def test_registrar_excepcion_usuario_inexistente_lanza_usuario_no_encontrado(
        self, reputacion_service, excepcion_repo
    ):
        """RF-23: UUID no registrado -> UsuarioNoEncontrado y sin excepción huérfana."""
        ahora = datetime.now(UTC)
        usuario_fantasma = uuid4()

        with pytest.raises(UsuarioNoEncontrado):
            reputacion_service.registrar_excepcion(
                usuario_fantasma, "Motivo", ahora, ahora + timedelta(days=5)
            )

        assert excepcion_repo.obtener_vigentes_por_usuario(usuario_fantasma) == []


@pytest.mark.integration
class TestPremiarDevolucionPuntual:
    """Tests para premiar_devolucion_puntual (RF-10)."""

    def test_premiar_usuario_sin_perfil_lo_crea_y_suma_10(self, reputacion_service, perfil_repo, usuario_creado):
        """RF-10: sin perfil se crea con la factory (500, NORMAL) y recibe el premio (510), persistido."""
        reputacion_service.premiar_devolucion_puntual(usuario_creado)

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil is not None
        assert perfil.puntaje.puntos == 510
        assert perfil.nivel == NivelReputacion.NORMAL

    def test_premiar_recalcula_el_nivel(self, reputacion_service, perfil_repo, usuario_creado):
        """RF-10: el premio recalcula el nivel (290 BAJO -> 300 NORMAL) y se persiste."""
        reputacion_service.obtener_perfil(usuario_creado)
        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        perfil.puntaje = perfil.puntaje.restar(210)  # 500 - 210 = 290 -> BAJO
        perfil.recalcular_nivel()
        perfil_repo.guardar(perfil)
        assert perfil.nivel == NivelReputacion.BAJO

        reputacion_service.premiar_devolucion_puntual(usuario_creado)

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil.puntaje.puntos == 300
        assert perfil.nivel == NivelReputacion.NORMAL

    def test_premiar_usuario_inexistente_lanza_usuario_no_encontrado(self, reputacion_service, perfil_repo):
        """RF-23: UUID no registrado -> UsuarioNoEncontrado y sin perfil huérfano."""
        usuario_fantasma = uuid4()

        with pytest.raises(UsuarioNoEncontrado):
            reputacion_service.premiar_devolucion_puntual(usuario_fantasma)

        assert perfil_repo.obtener_por_usuario(usuario_fantasma) is None


@pytest.mark.integration
class TestEjecutarAmnistiaMensual:
    """Tests para ejecutar_amnistia_mensual (RF-11, RF-12, RF-13)."""

    @staticmethod
    def _segundo_usuario(auth_service) -> UUID:
        """Crea otro usuario real (correo distinto) para escenarios con varios perfiles."""
        return auth_service.registrar_usuario(
            CrearUsuarioDTO(
                nombre="Otra Persona",
                correo=f"otra-{uuid4().hex}@example.com",
                telefono="+34 600 222 333",
                password="Password123",
            )
        ).usuario.id

    @staticmethod
    def _perfil_bajo(perfil_repo, usuario_id, sanciones=()):
        """Crea un perfil BAJO (280) con las sanciones indicadas (montaje vía repositorio)."""
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        perfil.puntaje = perfil.puntaje.restar(220)  # 500 - 220 = 280 -> BAJO
        for sancion in sanciones:
            perfil.aplicar_sancion(sancion)
        perfil.recalcular_nivel()
        perfil_repo.guardar(perfil)
        return perfil

    def test_amnistia_premia_solo_lo_elegible_y_devuelve_el_conteo(
        self, reputacion_service, perfil_repo, auth_service, usuario_creado
    ):
        """RF-11/RF-12: premia el BAJO sin sanciones recientes y excluye el que tiene una reciente."""
        otro_usuario = self._segundo_usuario(auth_service)
        self._perfil_bajo(perfil_repo, usuario_creado)  # 280, sin sanciones -> premiado
        self._perfil_bajo(
            perfil_repo,
            otro_usuario,
            sanciones=[
                Sancion(
                    id=uuid4(),
                    tipo=TipoSancion.DANO_PARCIAL,
                    puntos_descuento=-30,
                    monto_descuento=Decimal(50),
                    motivo="Sanción reciente",
                    fecha_aplicacion=datetime.now(UTC) - timedelta(days=10),
                    fecha_fin=datetime.now(UTC) + timedelta(days=20),
                    activa=True,
                )
            ],
        )

        premiados = reputacion_service.ejecutar_amnistia_mensual()

        assert premiados == 1
        perfil_premiado = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil_premiado.puntaje.puntos == 305  # 280 + 25
        assert perfil_premiado.nivel == NivelReputacion.NORMAL  # 305 > 299
        perfil_excluido = perfil_repo.obtener_por_usuario(otro_usuario)
        assert perfil_excluido.puntaje.puntos == 250  # 280 - 30, sin +25

    def test_amnistia_no_premia_niveles_distintos_de_bajo_y_devuelve_cero(
        self, reputacion_service, perfil_repo, usuario_creado
    ):
        """RF-12: un perfil NORMAL no recibe amnistía; el conteo 0 es un resultado válido."""
        reputacion_service.obtener_perfil(usuario_creado)  # 500 -> NORMAL

        assert reputacion_service.ejecutar_amnistia_mensual() == 0

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil.puntaje.puntos == 500

    def test_amnistia_premia_pero_no_desbloquea_el_prestamo(self, reputacion_service, perfil_repo, usuario_creado):
        """RF-12 (caso límite 5): +25 con una sanción de hace 35 días; sigue sin ser elegible."""
        sancion_antigua = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_TOTAL,
            puntos_descuento=-100,
            monto_descuento=Decimal("300.00"),
            motivo="Pérdida de recurso",
            fecha_aplicacion=datetime.now(UTC) - timedelta(days=35),
            fecha_fin=datetime.now(UTC) + timedelta(days=25),  # bloqueo de 60 días
            activa=True,
        )
        self._perfil_bajo(perfil_repo, usuario_creado, sanciones=[sancion_antigua])
        # 280 - 100 = 180 (BAJO); la sanción sigue vigente -> bloqueante

        assert reputacion_service.ejecutar_amnistia_mensual() == 1

        perfil = perfil_repo.obtener_por_usuario(usuario_creado)
        assert perfil.puntaje.puntos == 205  # 180 + 25
        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is False


@pytest.mark.integration
class TestObtenerElegibilidad:
    """Tests para obtener_elegibilidad (RF-21)."""

    def test_obtener_elegibilidad_elegible_sin_razon(self, reputacion_service, usuario_creado):
        """RF-21: sin sanciones bloqueantes -> elegible y sin razón."""
        elegibilidad = reputacion_service.obtener_elegibilidad(usuario_creado)

        assert isinstance(elegibilidad, ElegibilidadDTO)
        assert elegibilidad.elegible is True
        assert elegibilidad.razon is None

    def test_obtener_elegibilidad_sin_perfil_lo_crea_y_es_elegible(
        self, reputacion_service, perfil_repo, usuario_creado
    ):
        """RF-21: sin perfil se autocrea (mismo criterio que es_elegible_para_prestamo)."""
        assert perfil_repo.obtener_por_usuario(usuario_creado) is None

        elegibilidad = reputacion_service.obtener_elegibilidad(usuario_creado)

        assert elegibilidad.elegible is True
        assert perfil_repo.obtener_por_usuario(usuario_creado) is not None

    def test_obtener_elegibilidad_no_elegible_incluye_tipo_y_fecha_de_fin(
        self, reputacion_service, perfil_repo, usuario_creado
    ):
        """RF-21: la razón incluye el tipo de la sanción bloqueante y su fecha de fin."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Tardanza", dias_retardo=3)
        sancion = perfil_repo.obtener_por_usuario(usuario_creado).sanciones[0]

        elegibilidad = reputacion_service.obtener_elegibilidad(usuario_creado)

        assert elegibilidad.elegible is False
        assert elegibilidad.razon is not None
        assert "TARDANZA" in elegibilidad.razon
        assert sancion.fecha_fin.strftime("%Y-%m-%d") in elegibilidad.razon

    def test_obtener_elegibilidad_con_excepcion_vigente_es_elegible(self, reputacion_service, usuario_creado):
        """RF-21/RF-15: una excepción vigente cubre la TARDANZA -> elegible sin razón."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Tardanza", dias_retardo=3)
        ahora = datetime.now(UTC)
        reputacion_service.registrar_excepcion(
            usuario_creado, "Examen final", ahora - timedelta(days=1), ahora + timedelta(days=1)
        )

        elegibilidad = reputacion_service.obtener_elegibilidad(usuario_creado)

        assert elegibilidad.elegible is True
        assert elegibilidad.razon is None


@pytest.mark.integration
class TestAnularExcepcion:
    """Tests para anular_excepcion (RF-22, RF-23)."""

    def test_anular_excepcion_la_marca_inactiva_y_persiste(
        self, reputacion_service, excepcion_repo, usuario_creado
    ):
        """RF-22: anular deja activa=False y lo persiste; devuelve el DTO de la excepción."""
        ahora = datetime.now(UTC)
        creada = reputacion_service.registrar_excepcion(
            usuario_creado, "Registrada por error", ahora, ahora + timedelta(days=5)
        )

        anulada = reputacion_service.anular_excepcion(creada.id)

        assert isinstance(anulada, ExcepcionAcademicaDTO)
        assert anulada.id == creada.id
        assert anulada.activa is False
        persistida = excepcion_repo.obtener_por_id(creada.id)
        assert persistida is not None
        assert persistida.activa is False

    def test_anular_excepcion_es_idempotente(self, reputacion_service, usuario_creado):
        """RF-22: anular una excepción ya anulada no falla; devuelve la excepción anulada."""
        ahora = datetime.now(UTC)
        creada = reputacion_service.registrar_excepcion(
            usuario_creado, "Motivo", ahora, ahora + timedelta(days=5)
        )

        primera = reputacion_service.anular_excepcion(creada.id)
        segunda = reputacion_service.anular_excepcion(creada.id)

        assert primera.activa is False
        assert segunda.activa is False
        assert segunda.id == creada.id

    def test_anular_excepcion_inexistente_lanza_excepcion_no_encontrada(self, reputacion_service):
        """RF-22/RF-23: identificador inexistente -> ExcepcionNoEncontrada (la API lo traduce a 404)."""
        with pytest.raises(ExcepcionNoEncontrada):
            reputacion_service.anular_excepcion(uuid4())

    def test_anular_excepcion_deja_de_cubrir_la_sancion(self, reputacion_service, usuario_creado):
        """RF-22/RF-14: al anular, la excepción deja de cubrir la TARDANZA en la elegibilidad."""
        reputacion_service.aplicar_sancion(usuario_creado, TipoSancion.TARDANZA, "Tardanza", dias_retardo=3)
        ahora = datetime.now(UTC)
        excepcion = reputacion_service.registrar_excepcion(
            usuario_creado, "Examen final", ahora - timedelta(days=1), ahora + timedelta(days=1)
        )
        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is True

        reputacion_service.anular_excepcion(excepcion.id)

        assert reputacion_service.es_elegible_para_prestamo(usuario_creado) is False


@pytest.mark.integration
class TestObtenerPerfilGestion:
    """Tests para obtener_perfil_gestion (RF-04, D5, RNF-2): solo lectura para gestión."""

    def test_obtener_perfil_gestion_usuario_sin_perfil_no_crea_perfil(
        self, reputacion_service, perfil_repo, usuario_creado
    ):
        """RF-04/D5: sin perfil devuelve 500/NORMAL en memoria y no deja fila nueva."""
        ficha = reputacion_service.obtener_perfil_gestion(usuario_creado)

        assert isinstance(ficha, PerfilGestionDTO)
        assert ficha.usuario_id == usuario_creado
        assert ficha.puntaje == 500
        assert ficha.nivel == NivelReputacion.NORMAL
        assert ficha.fecha_actualizacion is None
        assert ficha.sanciones == []
        # La lectura no puede autocrear el perfil (RNF-2)
        assert perfil_repo.obtener_por_usuario(usuario_creado) is None

    def test_obtener_perfil_gestion_sin_perfil_devuelve_excepciones_reales(
        self, reputacion_service, excepcion_repo, usuario_creado
    ):
        """RF-04: usuario sin perfil con una excepción real -> la devuelve con su estado."""
        ahora = datetime.now(UTC)
        excepcion = ExcepcionAcademica(
            usuario_id=usuario_creado,
            motivo="Examen final",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )
        excepcion_repo.guardar(excepcion)

        ficha = reputacion_service.obtener_perfil_gestion(usuario_creado)

        assert ficha.fecha_actualizacion is None
        assert ficha.sanciones == []
        assert len(ficha.excepciones) == 1
        assert ficha.excepciones[0].id == excepcion.id
        assert ficha.excepciones[0].motivo == "Examen final"
        assert ficha.excepciones[0].activa is True
        assert ficha.excepciones[0].estado == EstadoExcepcion.VIGENTE
        assert ficha.excepciones[0].vigente is True

    def test_obtener_perfil_gestion_con_perfil_y_sancion(
        self, reputacion_service, usuario_creado
    ):
        """RF-04: con perfil sancionado, la ficha trae la sanción real y el puntaje descontado."""
        sancion_dto = reputacion_service.aplicar_sancion(
            usuario_creado, TipoSancion.TARDANZA, "Devolución tardía", dias_retardo=3
        )

        ficha = reputacion_service.obtener_perfil_gestion(usuario_creado)

        assert ficha.puntaje == 490  # 500 - 10
        assert ficha.nivel == NivelReputacion.NORMAL
        assert ficha.fecha_actualizacion is not None
        assert len(ficha.sanciones) == 1
        assert isinstance(ficha.sanciones[0], SancionDTO)
        assert ficha.sanciones[0].id == sancion_dto.id
        assert ficha.sanciones[0].fecha_fin == sancion_dto.fecha_fin
        assert ficha.sanciones[0].vigente is True

    def test_obtener_perfil_gestion_usuario_inexistente(self, reputacion_service):
        """RF-04/RF-23: un UUID no registrado lanza UsuarioNoEncontrado (la API lo traduce a 404)."""
        with pytest.raises(UsuarioNoEncontrado):
            reputacion_service.obtener_perfil_gestion(uuid4())

    def test_obtener_perfil_gestion_no_modifica_excepciones(
        self, reputacion_service, excepcion_repo, usuario_creado
    ):
        """RNF-2: la consulta no cambia el número ni el estado de las excepciones."""
        ahora = datetime.now(UTC)
        excepcion_vigente = ExcepcionAcademica(
            usuario_id=usuario_creado,
            motivo="Examen final",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
        )
        excepcion_anulada = ExcepcionAcademica(
            usuario_id=usuario_creado,
            motivo="Registrada por error",
            fecha_inicio=ahora - timedelta(days=5),
            fecha_fin=ahora + timedelta(days=5),
            activa=False,
        )
        excepcion_repo.guardar(excepcion_vigente)
        excepcion_repo.guardar(excepcion_anulada)
        antes = excepcion_repo.obtener_por_usuario(usuario_creado)

        ficha = reputacion_service.obtener_perfil_gestion(usuario_creado)

        despues = excepcion_repo.obtener_por_usuario(usuario_creado)
        assert len(ficha.excepciones) == 2
        assert len(despues) == len(antes) == 2
        assert {e.id: e.activa for e in despues} == {e.id: e.activa for e in antes}