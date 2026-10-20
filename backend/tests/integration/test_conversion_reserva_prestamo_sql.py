from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.infrastructure.models.prestamo_model import PrestamoModel
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_prestamo_repository import (
    SqlPrestamoRepository,
)
from prestamos_recursos.contexts.reservas.application.reserva_service import ReservaService
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.contexts.reservas.infrastructure.models.reserva_model import ReservaModel
from prestamos_recursos.contexts.reservas.infrastructure.repositories.sql_reserva_repository import (
    SqlReservaRepository,
)
from prestamos_recursos.shared.database import Base


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS reservas")
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS prestamos")
        Base.metadata.create_all(connection)
    return Session(engine, expire_on_commit=False)


def make_service(session: Session) -> ReservaService:
    return ReservaService(
        SqlReservaRepository(session),
        PrestamoService(
            prestamo_repository=SqlPrestamoRepository(session),
            checklist_repository=None,
            garantia_repository=None,
        ),
    )


def test_conversion_persiste_prestamo_y_reserva_en_una_transaccion():
    session = make_session()
    reserva_id = uuid4()
    usuario_id = uuid4()
    recurso_id = uuid4()
    fecha_inicio = datetime(2026, 10, 6, tzinfo=UTC)
    fecha_fin = datetime(2026, 10, 7, tzinfo=UTC)
    session.add(
        ReservaModel(
            id=reserva_id,
            usuario_id=usuario_id,
            recurso_id=recurso_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=EstadoReserva.CONFIRMADA,
        )
    )
    session.commit()

    service = make_service(session)
    with session.begin():
        assert service.convertir_a_prestamo(reserva_id) is True
        assert service.convertir_a_prestamo(reserva_id) is False

    prestamo = SqlPrestamoRepository(session).obtener_por_id(
        session.query(PrestamoModel.id).scalar()
    )
    reserva = SqlReservaRepository(session).obtener_por_id(reserva_id)

    assert prestamo is not None
    assert prestamo.reserva_id == reserva_id
    assert prestamo.usuario_id == usuario_id
    assert prestamo.recurso_id == recurso_id
    assert prestamo.estado == EstadoPrestamo.ACTIVO
    assert session.query(PrestamoModel).count() == 1
    assert reserva is not None
    assert reserva.estado == EstadoReserva.CONVERTIDA


def test_conversion_no_persiste_prestamo_si_reserva_no_esta_confirmada():
    session = make_session()
    reserva_id = uuid4()
    session.add(
        ReservaModel(
            id=reserva_id,
            usuario_id=uuid4(),
            recurso_id=uuid4(),
            fecha_inicio=datetime(2026, 10, 6, tzinfo=UTC),
            fecha_fin=datetime(2026, 10, 7, tzinfo=UTC),
            estado=EstadoReserva.PENDIENTE,
        )
    )
    session.commit()

    with session.begin():
        assert make_service(session).convertir_a_prestamo(reserva_id) is False

    assert session.query(PrestamoModel).count() == 0
    assert SqlReservaRepository(session).obtener_por_id(reserva_id).estado == EstadoReserva.PENDIENTE