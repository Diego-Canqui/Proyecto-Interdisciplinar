"""Tests de integración para SqlExcepcionAcademicaRepository (infrastructure + DB)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.excepcion_academica_model import (
    ExcepcionAcademicaModel,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_excepcion_academica_repository import (
    SqlExcepcionAcademicaRepository,
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
def excepcion_repo(db_session):
    return SqlExcepcionAcademicaRepository(db_session)


@pytest.fixture
def usuario_id() -> UUID:
    return uuid4()


@pytest.mark.integration
class TestSqlExcepcionAcademicaRepository:
    """Tests para SqlExcepcionAcademicaRepository."""

    def test_guardar_crea_excepcion_nueva(self, excepcion_repo, usuario_id, db_session):
        """RF-19, RF-21: Guardar crea una excepción nueva."""
        ahora = datetime.now(UTC)
        inicio = ahora + timedelta(days=1)
        fin = ahora + timedelta(days=30)
        
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Enfermedad",
            fecha_inicio=inicio,
            fecha_fin=fin,
            activa=True,
        )

        excepcion_repo.guardar(excepcion)

        # Verificar en BD
        modelo = db_session.query(ExcepcionAcademicaModel).filter_by(id=excepcion.id).one()
        assert modelo.id == excepcion.id
        assert modelo.usuario_id == usuario_id
        assert modelo.motivo == "Enfermedad"
        assert modelo.fecha_inicio == inicio
        assert modelo.fecha_fin == fin
        assert modelo.activa is True

    def test_guardar_upsert_actualiza_excepcion_existente(self, excepcion_repo, usuario_id, db_session):
        """RF-19, RF-21: Guardar actualiza excepción existente (upsert por ID)."""
        ahora = datetime.now(UTC)
        inicio = ahora + timedelta(days=1)
        fin = ahora + timedelta(days=30)
        
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Original",
            fecha_inicio=inicio,
            fecha_fin=fin,
            activa=True,
        )
        excepcion_repo.guardar(excepcion)

        # Modificar y guardar de nuevo
        excepcion.motivo = "Actualizado"
        excepcion.activa = False
        excepcion_repo.guardar(excepcion)

        # Verificar que se actualizó (no duplicado)
        modelos = db_session.query(ExcepcionAcademicaModel).filter_by(id=excepcion.id).all()
        assert len(modelos) == 1
        assert modelos[0].motivo == "Actualizado"
        assert modelos[0].activa is False

    def test_obtener_por_id_retorna_excepcion(self, excepcion_repo, usuario_id, db_session):
        """RF-19, RF-21: Obtener por ID retorna ExcepcionAcademica."""
        ahora = datetime.now(UTC)
        inicio = ahora + timedelta(days=1)
        fin = ahora + timedelta(days=30)
        
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Test",
            fecha_inicio=inicio,
            fecha_fin=fin,
            activa=True,
        )
        excepcion_repo.guardar(excepcion)

        obtenida = excepcion_repo.obtener_por_id(excepcion.id)

        assert obtenida is not None
        assert obtenida.id == excepcion.id
        assert obtenida.usuario_id == usuario_id
        assert obtenida.motivo == "Test"
        assert obtenida.fecha_inicio == inicio
        assert obtenida.fecha_fin == fin
        assert obtenida.activa is True

    def test_obtener_por_id_inexistente_retorna_none(self, excepcion_repo):
        """RF-19, RF-21: Obtener por ID inexistente retorna None."""
        obtenida = excepcion_repo.obtener_por_id(uuid4())
        assert obtenida is None

    def test_obtener_vigentes_por_usuario_filtra_activa_y_fechas(self, excepcion_repo, usuario_id, db_session):
        """RF-19, RF-21: Obtener vigentes filtra por activa=True y rango de fechas."""
        ahora = datetime.now(UTC)
        
        # Excepción 1: vigente (activa, fechas correctas)
        excepcion_vigente = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Vigente",
            fecha_inicio=ahora - timedelta(days=5),
            fecha_fin=ahora + timedelta(days=5),
            activa=True,
        )
        
        # Excepción 2: no vigente (activa=False)
        excepcion_inactiva = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Inactiva",
            fecha_inicio=ahora - timedelta(days=5),
            fecha_fin=ahora + timedelta(days=5),
            activa=False,
        )
        
        # Excepción 3: no vigente (fecha_inicio en el futuro)
        excepcion_futura = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Futura",
            fecha_inicio=ahora + timedelta(days=10),
            fecha_fin=ahora + timedelta(days=20),
            activa=True,
        )
        
        # Excepción 4: no vigente (fecha_fin en el pasado)
        excepcion_pasada = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Pasada",
            fecha_inicio=ahora - timedelta(days=20),
            fecha_fin=ahora - timedelta(days=10),
            activa=True,
        )
        
        # Excepción 5: de otro usuario (no debe aparecer)
        excepcion_otro_usuario = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),  # Otro usuario
            motivo="Otro usuario",
            fecha_inicio=ahora - timedelta(days=5),
            fecha_fin=ahora + timedelta(days=5),
            activa=True,
        )
        
        for e in [excepcion_vigente, excepcion_inactiva, excepcion_futura, excepcion_pasada, excepcion_otro_usuario]:
            excepcion_repo.guardar(e)

        # Obtener vigentes
        vigentes = excepcion_repo.obtener_vigentes_por_usuario(usuario_id)

        assert len(vigentes) == 1
        assert vigentes[0].id == excepcion_vigente.id
        assert vigentes[0].motivo == "Vigente"

    def test_obtener_vigentes_por_usuario_sin_vigentes_retorna_lista_vacia(self, excepcion_repo, usuario_id):
        """RF-19, RF-21: Sin excepciones vigentes retorna lista vacía."""
        vigentes = excepcion_repo.obtener_vigentes_por_usuario(usuario_id)
        assert vigentes == []

    def test_obtener_vigentes_por_usuario_multiples_vigentes(self, excepcion_repo, usuario_id, db_session):
        """RF-19, RF-21: Retorna múltiples excepciones vigentes."""
        ahora = datetime.now(UTC)
        
        excepcion1 = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Vigente 1",
            fecha_inicio=ahora - timedelta(days=5),
            fecha_fin=ahora + timedelta(days=5),
            activa=True,
        )
        excepcion2 = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Vigente 2",
            fecha_inicio=ahora - timedelta(days=2),
            fecha_fin=ahora + timedelta(days=10),
            activa=True,
        )
        
        excepcion_repo.guardar(excepcion1)
        excepcion_repo.guardar(excepcion2)

        vigentes = excepcion_repo.obtener_vigentes_por_usuario(usuario_id)

        assert len(vigentes) == 2
        motivos = {v.motivo for v in vigentes}
        assert motivos == {"Vigente 1", "Vigente 2"}

    def test_guardar_y_obtener_vigentes_con_fechas_naive(self, excepcion_repo, usuario_id, db_session):
        """RF-19, RF-21: Fechas naive (sin tz) se manejan correctamente."""
        ahora = datetime.now(UTC)
        # Fechas naive (sin timezone)
        inicio = (ahora - timedelta(days=1)).replace(tzinfo=None)
        fin = (ahora + timedelta(days=1)).replace(tzinfo=None)
        
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Fechas naive",
            fecha_inicio=inicio,
            fecha_fin=fin,
            activa=True,
        )
        excepcion_repo.guardar(excepcion)

        vigentes = excepcion_repo.obtener_vigentes_por_usuario(usuario_id)

        assert len(vigentes) == 1
        assert vigentes[0].motivo == "Fechas naive"

    def test_excepcion_vigente_respeta_metodo_es_vigente(self, excepcion_repo, usuario_id, db_session):
        """RF-21: Las excepciones retornadas cumplen es_vigente() == True."""
        ahora = datetime.now(UTC)
        
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Test es_vigente",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )
        excepcion_repo.guardar(excepcion)

        vigentes = excepcion_repo.obtener_vigentes_por_usuario(usuario_id)

        assert len(vigentes) == 1
        assert vigentes[0].es_vigente() is True