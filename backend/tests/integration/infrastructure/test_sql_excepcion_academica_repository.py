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
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.usuario_model import (
    UsuarioModel,
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
def usuario_factory(db_session):
    """Crea usuarios reales en BD (la FK excepciones_academicas.usuario_id lo exige)."""

    def _crear() -> UUID:
        usuario = UsuarioModel(
            id=uuid4(),
            nombre="Usuario Test",
            correo=f"usuario-{uuid4().hex}@test.com",
            password_hash="hash-ficticio-de-prueba",  # ficticio: nunca se verifica
            roles=["ESTUDIANTE"],
        )
        db_session.add(usuario)
        db_session.flush()
        return usuario.id

    return _crear


@pytest.fixture
def usuario_id(usuario_factory) -> UUID:
    return usuario_factory()


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

    def test_obtener_vigentes_por_usuario_filtra_activa_y_fechas(self, excepcion_repo, usuario_id, usuario_factory, db_session):
        """RF-19, RF-21: Obtener vigentes filtra por activa=True y rango de fechas."""
        ahora = datetime.now(UTC)
        otro_usuario_id = usuario_factory()
        
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
            usuario_id=otro_usuario_id,  # Otro usuario
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

    def test_obtener_por_usuario_devuelve_todas(self, excepcion_repo, usuario_id):
        """RF-04: devuelve todas las excepciones del usuario, sin filtrar por vigencia."""
        ahora = datetime.now(UTC)

        excepciones = [
            ExcepcionAcademica(
                id=uuid4(),
                usuario_id=usuario_id,
                motivo="Vigente",
                fecha_inicio=ahora - timedelta(days=5),
                fecha_fin=ahora + timedelta(days=5),
                activa=True,
            ),
            ExcepcionAcademica(
                id=uuid4(),
                usuario_id=usuario_id,
                motivo="Vencida activa",
                fecha_inicio=ahora - timedelta(days=20),
                fecha_fin=ahora - timedelta(days=10),
                activa=True,
            ),
            ExcepcionAcademica(
                id=uuid4(),
                usuario_id=usuario_id,
                motivo="Anulada",
                fecha_inicio=ahora - timedelta(days=5),
                fecha_fin=ahora + timedelta(days=5),
                activa=False,
            ),
            ExcepcionAcademica(
                id=uuid4(),
                usuario_id=usuario_id,
                motivo="Programada",
                fecha_inicio=ahora + timedelta(days=10),
                fecha_fin=ahora + timedelta(days=20),
                activa=True,
            ),
        ]
        for excepcion in excepciones:
            excepcion_repo.guardar(excepcion)

        obtenidas = excepcion_repo.obtener_por_usuario(usuario_id)

        assert len(obtenidas) == 4
        assert {e.id for e in obtenidas} == {e.id for e in excepciones}
        motivos = {e.motivo for e in obtenidas}
        assert motivos == {"Vigente", "Vencida activa", "Anulada", "Programada"}

    def test_obtener_por_usuario_sin_excepciones(self, excepcion_repo, usuario_id):
        """RF-04: un usuario sin filas devuelve lista vacía."""
        assert excepcion_repo.obtener_por_usuario(usuario_id) == []

    def test_obtener_por_usuario_orden_por_inicio_desc(self, excepcion_repo, usuario_id):
        """RF-04: ordena por fecha de inicio descendente (la más reciente primero)."""
        ahora = datetime.now(UTC)

        mas_antigua = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Más antigua",
            fecha_inicio=ahora - timedelta(days=30),
            fecha_fin=ahora - timedelta(days=20),
            activa=True,
        )
        intermedia = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Intermedia",
            fecha_inicio=ahora - timedelta(days=10),
            fecha_fin=ahora + timedelta(days=5),
            activa=True,
        )
        mas_reciente = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=usuario_id,
            motivo="Más reciente",
            fecha_inicio=ahora + timedelta(days=10),
            fecha_fin=ahora + timedelta(days=20),
            activa=True,
        )
        # Se guardan desordenadas a propósito para comprobar que ordena la consulta
        for excepcion in [intermedia, mas_antigua, mas_reciente]:
            excepcion_repo.guardar(excepcion)

        obtenidas = excepcion_repo.obtener_por_usuario(usuario_id)

        assert [e.id for e in obtenidas] == [
            mas_reciente.id,
            intermedia.id,
            mas_antigua.id,
        ]

    def test_obtener_por_usuario_no_mezcla_usuarios(
        self, excepcion_repo, usuario_id, usuario_factory
    ):
        """RF-04: cada usuario recibe solo sus propias excepciones."""
        ahora = datetime.now(UTC)
        otro_usuario_id = usuario_factory()

        propias = [
            ExcepcionAcademica(
                id=uuid4(),
                usuario_id=usuario_id,
                motivo="Propia 1",
                fecha_inicio=ahora - timedelta(days=5),
                fecha_fin=ahora + timedelta(days=5),
                activa=True,
            ),
            ExcepcionAcademica(
                id=uuid4(),
                usuario_id=usuario_id,
                motivo="Propia 2",
                fecha_inicio=ahora - timedelta(days=15),
                fecha_fin=ahora - timedelta(days=10),
                activa=True,
            ),
        ]
        ajena = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=otro_usuario_id,
            motivo="Ajena",
            fecha_inicio=ahora - timedelta(days=5),
            fecha_fin=ahora + timedelta(days=5),
            activa=True,
        )
        for excepcion in [*propias, ajena]:
            excepcion_repo.guardar(excepcion)

        del_usuario = excepcion_repo.obtener_por_usuario(usuario_id)
        del_otro_usuario = excepcion_repo.obtener_por_usuario(otro_usuario_id)

        assert len(del_usuario) == 2
        assert {e.id for e in del_usuario} == {e.id for e in propias}
        assert len(del_otro_usuario) == 1
        assert del_otro_usuario[0].id == ajena.id