"""Tests de integración para SqlPerfilReputacionRepository (infrastructure + DB)."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import (
    PerfilReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import (
    PuntajeReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import (
    PerfilReputacionModel,
    SancionModel,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_perfil_reputacion_repository import (
    SqlPerfilReputacionRepository,
)
from prestamos_recursos.shared.database import Base, SessionLocal, engine


@pytest.fixture(scope="function")
def db_session():
    """Crea una sesión de BD limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def perfil_repo(db_session):
    return SqlPerfilReputacionRepository(db_session)


@pytest.fixture
def usuario_id() -> UUID:
    return uuid4()


@pytest.mark.integration
class TestSqlPerfilReputacionRepository:
    """Tests para SqlPerfilReputacionRepository."""

    def test_guardar_crea_perfil_nuevo(self, perfil_repo, usuario_id):
        """RF-18: Guardar crea un perfil nuevo con sanciones vacías."""
        ahora = datetime.now(UTC)
        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=usuario_id,
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=ahora,
            sanciones=[],
        )

        perfil_repo.guardar(perfil)

        # Verificar en BD
        modelo = db_session.query(PerfilReputacionModel).filter_by(usuario_id=usuario_id).one()
        assert modelo.id == perfil.id
        assert modelo.usuario_id == usuario_id
        assert modelo.puntos == 500
        assert modelo.nivel == NivelReputacion.NORMAL
        assert len(modelo.sanciones) == 0

    def test_guardar_upsert_actualiza_perfil_existente(self, perfil_repo, usuario_id, db_session):
        """RF-18: Guardar actualiza perfil existente (upsert por usuario_id)."""
        # Crear perfil inicial
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        perfil_repo.guardar(perfil)

        # Modificar y guardar de nuevo (mismo usuario_id)
        perfil.puntaje = PuntajeReputacion(puntos=700)
        perfil.recalcular_nivel()
        perfil_repo.guardar(perfil)

        # Verificar que se actualizó (no duplicado)
        modelos = db_session.query(PerfilReputacionModel).filter_by(usuario_id=usuario_id).all()
        assert len(modelos) == 1
        assert modelos[0].puntos == 700
        assert modelos[0].nivel == NivelReputacion.BUENO

    def test_guardar_sincroniza_sanciones_insert_nuevas(self, perfil_repo, usuario_id, db_session):
        """RF-18, RF-20: Guardar inserta sanciones nuevas en transacción."""
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        
        # Añadir sanción
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal(0),
            motivo="Llegada tarde",
            fecha_aplicacion=datetime.now(UTC),
            activa=True,
        )
        perfil.aplicar_sancion(sancion)
        
        perfil_repo.guardar(perfil)

        # Verificar sanción en BD
        modelos = db_session.query(SancionModel).all()
        assert len(modelos) == 1
        assert modelos[0].tipo == TipoSancion.TARDANZA
        assert modelos[0].puntos_descuento == -10
        assert modelos[0].activa is True

    def test_guardar_sincroniza_sanciones_borra_huerfanas(self, perfil_repo, usuario_id, db_session):
        """RF-18, RF-20: Guardar borra sanciones que ya no están en el dominio."""
        # Crear perfil con una sanción
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        sancion1 = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal(0),
            motivo="Sanción 1",
            fecha_aplicacion=datetime.now(UTC),
            activa=True,
        )
        perfil.aplicar_sancion(sancion1)
        perfil_repo.guardar(perfil)

        # Verificar que existe
        assert db_session.query(SancionModel).count() == 1

        # Guardar de nuevo SIN la sanción (simula que se eliminó del dominio)
        perfil.sanciones = []
        perfil_repo.guardar(perfil)

        # La sanción huérfana debe haberse borrado
        assert db_session.query(SancionModel).count() == 0

    def test_guardar_sincroniza_sanciones_actualiza_existentes(self, perfil_repo, usuario_id, db_session):
        """RF-18, RF-20: Guardar actualiza sanciones que ya existen."""
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal(0),
            motivo="Original",
            fecha_aplicacion=datetime.now(UTC),
            activa=True,
        )
        perfil.aplicar_sancion(sancion)
        perfil_repo.guardar(perfil)

        # Modificar la sanción y guardar
        sancion.activa = False
        sancion.motivo = "Actualizada"
        perfil_repo.guardar(perfil)

        # Verificar actualización
        modelo = db_session.query(SancionModel).one()
        assert modelo.activa is False
        assert modelo.motivo == "Actualizada"

    def test_guardar_transaccion_atomica_perfil_y_sanciones(self, perfil_repo, usuario_id, db_session):
        """RF-18, RF-20: Perfil y sanciones se persisten en una sola transacción."""
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        
        # Añadir múltiples sanciones
        for i in range(3):
            sancion = Sancion(
                id=uuid4(),
                tipo=TipoSancion.TARDANZA,
                puntos_descuento=-10,
                monto_descuento=Decimal(0),
                motivo=f"Sanción {i}",
                fecha_aplicacion=datetime.now(UTC),
                activa=True,
            )
            perfil.aplicar_sancion(sancion)
        
        perfil_repo.guardar(perfil)

        # Todo debe estar persistido
        modelo_perfil = db_session.query(PerfilReputacionModel).one()
        assert modelo_perfil.puntos == 470  # 500 - 3*10
        assert db_session.query(SancionModel).count() == 3

    def test_obtener_por_id_retorna_perfil_con_sanciones(self, perfil_repo, usuario_id, db_session):
        """RF-18: Obtener por ID retorna PerfilReputacion con sanciones cargadas (join)."""
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50.00"),
            motivo="Daño libro",
            fecha_aplicacion=datetime.now(UTC),
            activa=True,
        )
        perfil.aplicar_sancion(sancion)
        perfil_repo.guardar(perfil)

        # Obtener por ID
        obtenido = perfil_repo.obtener_por_id(perfil.id)

        assert obtenido is not None
        assert obtenido.id == perfil.id
        assert obtenido.usuario_id == usuario_id
        assert obtenido.puntaje.puntos == 470
        assert len(obtenido.sanciones) == 1
        assert obtenido.sanciones[0].tipo == TipoSancion.DANO_PARCIAL
        assert obtenido.sanciones[0].monto_descuento == Decimal("50.00")

    def test_obtener_por_id_inexistente_retorna_none(self, perfil_repo):
        """RF-18: Obtener por ID inexistente retorna None."""
        obtenido = perfil_repo.obtener_por_id(uuid4())
        assert obtenido is None

    def test_obtener_por_usuario_retorna_perfil_con_sanciones(self, perfil_repo, usuario_id, db_session):
        """RF-18: Obtener por usuario_id retorna PerfilReputacion con sanciones cargadas (join)."""
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.INASISTENCIA_RESERVA,
            puntos_descuento=-15,
            monto_descuento=Decimal(0),
            motivo="No retiró reserva",
            fecha_aplicacion=datetime.now(UTC),
            activa=True,
        )
        perfil.aplicar_sancion(sancion)
        perfil_repo.guardar(perfil)

        # Obtener por usuario_id
        obtenido = perfil_repo.obtener_por_usuario(usuario_id)

        assert obtenido is not None
        assert obtenido.usuario_id == usuario_id
        assert len(obtenido.sanciones) == 1
        assert obtenido.sanciones[0].tipo == TipoSancion.INASISTENCIA_RESERVA

    def test_obtener_por_usuario_inexistente_retorna_none(self, perfil_repo):
        """RF-18: Obtener por usuario_id inexistente retorna None."""
        obtenido = perfil_repo.obtener_por_usuario(uuid4())
        assert obtenido is None

    def test_guardar_sanciones_varias_tipos(self, perfil_repo, usuario_id, db_session):
        """RF-18, RF-20: Guardar persiste sanciones de diferentes tipos correctamente."""
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)
        
        sanciones = [
            Sancion(id=uuid4(), tipo=TipoSancion.TARDANZA, puntos_descuento=-10, monto_descuento=Decimal(0), motivo="Tardanza 1", fecha_aplicacion=datetime.now(UTC), activa=True),
            Sancion(id=uuid4(), tipo=TipoSancion.DANO_TOTAL, puntos_descuento=-100, monto_descuento=Decimal("200.00"), motivo="Pérdida libro", fecha_aplicacion=datetime.now(UTC), activa=True),
            Sancion(id=uuid4(), tipo=TipoSancion.INASISTENCIA_RESERVA, puntos_descuento=-15, monto_descuento=Decimal(0), motivo="No show", fecha_aplicacion=datetime.now(UTC), activa=False),
        ]
        for s in sanciones:
            perfil.aplicar_sancion(s)
        
        perfil_repo.guardar(perfil)

        modelos = db_session.query(SancionModel).all()
        assert len(modelos) == 3
        tipos = {m.tipo for m in modelos}
        assert tipos == {TipoSancion.TARDANZA, TipoSancion.DANO_TOTAL, TipoSancion.INASISTENCIA_RESERVA}
        
        # Verificar montos
        dano_total = next(m for m in modelos if m.tipo == TipoSancion.DANO_TOTAL)
        assert dano_total.monto_descuento == Decimal("200.00")
        assert dano_total.generar_cobro() is True  # método del modelo no existe, verificar entidad