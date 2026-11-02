from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.infrastructure.models.prestamo_model import PrestamoModel
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_prestamo_repository import (
    SqlPrestamoRepository,
)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS prestamos")
        PrestamoModel.__table__.create(connection)
    return Session(engine, expire_on_commit=False)


def test_guardar_y_obtener_por_id():
    session = make_session()
    repo = SqlPrestamoRepository(session)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 20, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 25, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )

    with session.begin():
        repo.guardar(prestamo)

    recuperado = repo.obtener_por_id(prestamo.id)
    assert recuperado is not None
    assert recuperado.id == prestamo.id
    assert recuperado.usuario_id == prestamo.usuario_id
    assert recuperado.estado == EstadoPrestamo.ACTIVO


def test_obtener_activos():
    session = make_session()
    repo = SqlPrestamoRepository(session)
    usuario_id = uuid4()

    p_activo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 20, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 25, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    p_devuelto = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 10, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 15, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )

    with session.begin():
        repo.guardar(p_activo)
        repo.guardar(p_devuelto)

    activos = repo.obtener_activos()
    assert len(activos) == 1
    assert activos[0].id == p_activo.id


def test_obtener_por_usuario():
    session = make_session()
    repo = SqlPrestamoRepository(session)
    usuario_1 = uuid4()
    usuario_2 = uuid4()

    p1 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_1,
        fecha_inicio=datetime(2026, 10, 20, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 25, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    p2 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_1,
        fecha_inicio=datetime(2026, 10, 10, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 15, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )
    p3 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_2,
        fecha_inicio=datetime(2026, 10, 10, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 15, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )

    with session.begin():
        repo.guardar(p1)
        repo.guardar(p2)
        repo.guardar(p3)

    prestamos_u1 = repo.obtener_por_usuario(usuario_1)
    assert len(prestamos_u1) == 2
    ids_u1 = {p.id for p in prestamos_u1}
    assert ids_u1 == {p1.id, p2.id}


def test_obtener_todos():
    session = make_session()
    repo = SqlPrestamoRepository(session)
    usuario_1 = uuid4()
    usuario_2 = uuid4()

    p1 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_1,
        fecha_inicio=datetime(2026, 10, 10, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 15, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )
    p2 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_2,
        fecha_inicio=datetime(2026, 10, 20, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 25, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )

    with session.begin():
        repo.guardar(p1)
        repo.guardar(p2)

    todos = repo.obtener_todos()
    assert len(todos) == 2
    # Ordenados por fecha_inicio desc
    assert todos[0].id == p2.id
    assert todos[1].id == p1.id
    assert {p.usuario_id for p in todos} == {usuario_1, usuario_2}
    assert {p.estado for p in todos} == {EstadoPrestamo.ACTIVO, EstadoPrestamo.DEVUELTO}


def test_obtener_todos_vacio():
    session = make_session()
    repo = SqlPrestamoRepository(session)
    assert repo.obtener_todos() == []


