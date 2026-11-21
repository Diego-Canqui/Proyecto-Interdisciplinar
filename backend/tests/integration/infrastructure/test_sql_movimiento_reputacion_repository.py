"""Tests de integración para SqlMovimientoReputacionRepository (infrastructure + DB)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.movimiento_reputacion import (
    MovimientoReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_movimiento_reputacion import (
    TipoMovimientoReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.movimiento_reputacion_model import (
    MovimientoReputacionModel,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import (
    PerfilReputacionModel,
    SancionModel,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.usuario_model import (
    UsuarioModel,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_movimiento_reputacion_repository import (
    SqlMovimientoReputacionRepository,
)


@pytest.fixture
def movimiento_repo(db_session) -> SqlMovimientoReputacionRepository:
    return SqlMovimientoReputacionRepository(db_session)


@pytest.fixture
def usuario_factory(db_session):
    """Crea usuarios reales en BD (FK movimientos_reputacion.usuario_id)."""

    def _crear() -> UUID:
        usuario = UsuarioModel(
            id=uuid4(),
            nombre="Usuario Bitácora",
            correo=f"bitacora-{uuid4().hex}@test.com",
            password_hash="hash-ficticio-de-prueba",
            roles=["ESTUDIANTE"],
        )
        db_session.add(usuario)
        db_session.flush()
        return usuario.id

    return _crear


@pytest.fixture
def sancion_factory(db_session):
    """Crea un perfil y una sanción real en BD (FK movimientos_reputacion.sancion_id)."""

    def _crear(usuario_id: UUID) -> UUID:
        perfil = (
            db_session.query(PerfilReputacionModel)
            .filter_by(usuario_id=usuario_id)
            .one_or_none()
        )
        if perfil is None:
            perfil = PerfilReputacionModel(
                id=uuid4(),
                usuario_id=usuario_id,
                puntos=490,
                nivel=NivelReputacion.NORMAL,
            )
            db_session.add(perfil)
            db_session.flush()

        sancion = SancionModel(
            id=uuid4(),
            perfil_reputacion_id=perfil.id,
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0.00"),
            motivo="Devolución tardía",
            fecha_aplicacion=datetime.now(UTC),
            fecha_fin=datetime.now(UTC) + timedelta(days=3),
            activa=True,
        )
        db_session.add(sancion)
        db_session.flush()
        return sancion.id

    return _crear


@pytest.fixture
def usuario_id(usuario_factory) -> UUID:
    return usuario_factory()


@pytest.mark.integration
class TestSqlMovimientoReputacionRepository:
    """Tests para SqlMovimientoReputacionRepository."""

    def test_registrar_y_obtener_por_usuario_persiste_campos(
        self, movimiento_repo, usuario_id, sancion_factory, db_session
    ) -> None:
        """RF-01, RF-04: registrar persiste todos los campos y referencias."""
        sancion_id = sancion_factory(usuario_id)
        prestamo_id = uuid4()
        reserva_id = uuid4()
        recurso_id = uuid4()
        fecha = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)

        movimiento = MovimientoReputacion(
            id=uuid4(),
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.SANCION,
            motivo="Devolución tardía de proyector",
            puntaje_anterior=500,
            variacion_puntos=-10,
            puntaje_resultante=490,
            fecha_movimiento=fecha,
            numero_secuencia=1,
            sancion_id=sancion_id,
            prestamo_id=prestamo_id,
            reserva_id=reserva_id,
            recurso_id=recurso_id,
            recurso_nombre="Proyector Epson X41",
        )

        movimiento_repo.registrar(movimiento)

        modelo = db_session.query(MovimientoReputacionModel).filter_by(id=movimiento.id).one()
        assert modelo.usuario_id == usuario_id
        assert modelo.tipo == TipoMovimientoReputacion.SANCION
        assert modelo.recurso_nombre == "Proyector Epson X41"

        obtenidos = movimiento_repo.obtener_por_usuario(usuario_id)
        assert len(obtenidos) == 1
        recuperado = obtenidos[0]
        assert recuperado == movimiento

    def test_registrar_soporta_referencias_opcionales_en_none_y_todos_los_tipos(
        self, movimiento_repo, usuario_id
    ) -> None:
        """RF-01: persiste todos los TipoMovimientoReputacion y campos opcionales nulos."""
        base = datetime(2026, 11, 18, 8, 0, tzinfo=UTC)
        tipos = list(TipoMovimientoReputacion)
        for indice, tipo in enumerate(tipos, start=1):
            mov = MovimientoReputacion(
                usuario_id=usuario_id,
                tipo=tipo,
                motivo=f"Evento {tipo.value}",
                puntaje_anterior=500,
                variacion_puntos=0,
                puntaje_resultante=500,
                fecha_movimiento=base + timedelta(minutes=indice),
                numero_secuencia=indice,
            )
            movimiento_repo.registrar(mov)

        obtenidos = movimiento_repo.obtener_por_usuario(usuario_id)
        assert len(obtenidos) == len(tipos)
        assert {m.tipo for m in obtenidos} == set(tipos)
        assert all(m.sancion_id is None and m.recurso_nombre is None for m in obtenidos)

    def test_registrar_solo_hace_flush_sin_commit_d13(
        self, movimiento_repo, usuario_id, db_session
    ) -> None:
        """RNF-2 (D13): registrar usa flush() y no hace commit()."""
        movimiento = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.BONIFICACION_ENTREGA_PUNTUAL,
            motivo="Entrega puntual",
            puntaje_anterior=500,
            variacion_puntos=5,
            puntaje_resultante=505,
        )

        movimiento_repo.registrar(movimiento)
        assert movimiento_repo.contar_por_usuario(usuario_id) == 1

        db_session.rollback()
        assert movimiento_repo.contar_por_usuario(usuario_id) == 0

    def test_registrar_no_permite_sobrescribir_id_existente(
        self, movimiento_repo, usuario_id, db_session
    ) -> None:
        """RF-04: repositorio append-only rechaza duplicar el mismo ID."""
        mov_id = uuid4()
        movimiento_repo.registrar(
            MovimientoReputacion(
                id=mov_id,
                usuario_id=usuario_id,
                tipo=TipoMovimientoReputacion.AMNISTIA_MENSUAL,
                motivo="Amnistía mensual",
                puntaje_anterior=200,
                variacion_puntos=25,
                puntaje_resultante=225,
            )
        )

        with pytest.raises(IntegrityError):
            movimiento_repo.registrar(
                MovimientoReputacion(
                    id=mov_id,
                    usuario_id=usuario_id,
                    tipo=TipoMovimientoReputacion.AMNISTIA_MENSUAL,
                    motivo="Intento de reemplazo",
                    puntaje_anterior=225,
                    variacion_puntos=25,
                    puntaje_resultante=250,
                )
            )
        db_session.rollback()

    def test_obtener_por_usuario_ordena_fecha_desc_y_secuencia_desc(
        self, movimiento_repo, usuario_id, usuario_factory
    ) -> None:
        """RF-04: ordena por (fecha_movimiento DESC, numero_secuencia DESC) y aísla por usuario."""
        otro_usuario_id = usuario_factory()
        t1 = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
        t2 = datetime(2026, 11, 18, 11, 0, tzinfo=UTC)
        t3 = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)

        m_antiguo = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.BONIFICACION_ENTREGA_PUNTUAL,
            motivo="Entrega antigua",
            puntaje_anterior=500,
            variacion_puntos=5,
            puntaje_resultante=505,
            fecha_movimiento=t1,
            numero_secuencia=1,
        )
        m_mismo_instante_seq1 = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.SANCION,
            motivo="Daño parcial",
            puntaje_anterior=505,
            variacion_puntos=-30,
            puntaje_resultante=475,
            fecha_movimiento=t2,
            numero_secuencia=1,
        )
        m_mismo_instante_seq2 = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.SANCION,
            motivo="Tardanza simultánea",
            puntaje_anterior=475,
            variacion_puntos=-10,
            puntaje_resultante=465,
            fecha_movimiento=t2,
            numero_secuencia=2,
        )
        m_reciente = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.BONIFICACION_DEVOLUCION_PUNTUAL,
            motivo="Devolución más reciente",
            puntaje_anterior=465,
            variacion_puntos=10,
            puntaje_resultante=475,
            fecha_movimiento=t3,
            numero_secuencia=3,
        )
        m_ajeno = MovimientoReputacion(
            usuario_id=otro_usuario_id,
            tipo=TipoMovimientoReputacion.AMNISTIA_MENSUAL,
            motivo="Movimiento de otro usuario",
            puntaje_anterior=200,
            variacion_puntos=25,
            puntaje_resultante=225,
            fecha_movimiento=t3,
            numero_secuencia=1,
        )

        # Insertar desordenados
        for mov in [m_mismo_instante_seq1, m_antiguo, m_ajeno, m_reciente, m_mismo_instante_seq2]:
            movimiento_repo.registrar(mov)

        obtenidos = movimiento_repo.obtener_por_usuario(usuario_id)
        assert [m.id for m in obtenidos] == [
            m_reciente.id,
            m_mismo_instante_seq2.id,
            m_mismo_instante_seq1.id,
            m_antiguo.id,
        ]
        assert movimiento_repo.obtener_por_usuario(uuid4()) == []

    def test_obtener_todos_retorna_orden_cronologico_desc(
        self, movimiento_repo, usuario_factory
    ) -> None:
        """RF-05: obtener_todos devuelve movimientos globales ordenados DESC."""
        assert movimiento_repo.obtener_todos() == []

        u1 = usuario_factory()
        u2 = usuario_factory()
        t1 = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
        t2 = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)

        m1 = MovimientoReputacion(
            usuario_id=u1,
            tipo=TipoMovimientoReputacion.BONIFICACION_ENTREGA_PUNTUAL,
            motivo="U1 primero",
            puntaje_anterior=500,
            variacion_puntos=5,
            puntaje_resultante=505,
            fecha_movimiento=t1,
            numero_secuencia=1,
        )
        m2 = MovimientoReputacion(
            usuario_id=u2,
            tipo=TipoMovimientoReputacion.SANCION,
            motivo="U2 primero en t2",
            puntaje_anterior=500,
            variacion_puntos=-10,
            puntaje_resultante=490,
            fecha_movimiento=t2,
            numero_secuencia=1,
        )
        m3 = MovimientoReputacion(
            usuario_id=u2,
            tipo=TipoMovimientoReputacion.SANCION,
            motivo="U2 segundo en t2",
            puntaje_anterior=490,
            variacion_puntos=-10,
            puntaje_resultante=480,
            fecha_movimiento=t2,
            numero_secuencia=2,
        )

        for mov in [m1, m3, m2]:
            movimiento_repo.registrar(mov)

        todos = movimiento_repo.obtener_todos()
        assert [m.id for m in todos] == [m3.id, m2.id, m1.id]

    def test_contar_por_usuario_y_obtener_siguiente_secuencia(
        self, movimiento_repo, usuario_factory
    ) -> None:
        """RF-01, RF-03: cuenta exacta por usuario y secuencia determinista."""
        u1 = usuario_factory()
        u2 = usuario_factory()

        assert movimiento_repo.contar_por_usuario(u1) == 0
        assert movimiento_repo.obtener_siguiente_secuencia(u1) == 1
        assert movimiento_repo.obtener_siguiente_secuencia(u2) == 1

        sec1 = movimiento_repo.obtener_siguiente_secuencia(u1)
        movimiento_repo.registrar(
            MovimientoReputacion(
                usuario_id=u1,
                tipo=TipoMovimientoReputacion.SALDO_INICIAL_HEREDADO,
                motivo="Saldo heredado",
                puntaje_anterior=500,
                variacion_puntos=-30,
                puntaje_resultante=470,
                numero_secuencia=sec1,
            )
        )
        assert movimiento_repo.contar_por_usuario(u1) == 1
        assert movimiento_repo.obtener_siguiente_secuencia(u1) == 2
        assert movimiento_repo.contar_por_usuario(u2) == 0
        assert movimiento_repo.obtener_siguiente_secuencia(u2) == 1

        sec2 = movimiento_repo.obtener_siguiente_secuencia(u1)
        movimiento_repo.registrar(
            MovimientoReputacion(
                usuario_id=u1,
                tipo=TipoMovimientoReputacion.BONIFICACION_DEVOLUCION_PUNTUAL,
                motivo="Devolución puntual",
                puntaje_anterior=470,
                variacion_puntos=10,
                puntaje_resultante=480,
                numero_secuencia=sec2,
            )
        )
        assert movimiento_repo.contar_por_usuario(u1) == 2
        assert movimiento_repo.obtener_siguiente_secuencia(u1) == 3

    def test_normalizacion_utc_en_escritura_y_lectura(
        self, movimiento_repo, usuario_id
    ) -> None:
        """RF-01: convierte zonas horarias a UTC y normaliza fechas naive leídas de SQLite."""
        tz_menos_5 = timezone(timedelta(hours=-5))
        fecha_con_offset = datetime(2026, 11, 18, 8, 30, tzinfo=tz_menos_5)
        fecha_naive = datetime(2026, 11, 18, 14, 0, tzinfo=UTC).replace(tzinfo=None)

        mov_offset = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.BONIFICACION_ENTREGA_PUNTUAL,
            motivo="Entrega con offset -05:00",
            puntaje_anterior=500,
            variacion_puntos=5,
            puntaje_resultante=505,
            fecha_movimiento=fecha_con_offset,
            numero_secuencia=1,
        )
        mov_naive = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.BONIFICACION_DEVOLUCION_PUNTUAL,
            motivo="Devolución naive",
            puntaje_anterior=505,
            variacion_puntos=10,
            puntaje_resultante=515,
            fecha_movimiento=fecha_naive,
            numero_secuencia=2,
        )

        movimiento_repo.registrar(mov_offset)
        movimiento_repo.registrar(mov_naive)

        por_usuario = movimiento_repo.obtener_por_usuario(usuario_id)
        assert len(por_usuario) == 2
        # 14:00 UTC es más reciente que 08:30-05:00 (= 13:30 UTC)
        assert por_usuario[0].id == mov_naive.id
        assert por_usuario[0].fecha_movimiento.tzinfo == UTC
        assert por_usuario[0].fecha_movimiento == datetime(2026, 11, 18, 14, 0, tzinfo=UTC)

        assert por_usuario[1].id == mov_offset.id
        assert por_usuario[1].fecha_movimiento.tzinfo == UTC
        assert por_usuario[1].fecha_movimiento == datetime(2026, 11, 18, 13, 30, tzinfo=UTC)

        todos = movimiento_repo.obtener_todos()
        assert todos[0].fecha_movimiento.tzinfo == UTC
        assert todos[1].fecha_movimiento.tzinfo == UTC
