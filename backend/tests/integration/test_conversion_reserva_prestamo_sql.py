from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.catalogo.infrastructure.models.recurso_model import RecursoModel
from prestamos_recursos.contexts.catalogo.infrastructure.repositories.sql_recurso_repository import (
    SqlRecursoRepository,
)
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


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS reservas")
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS prestamos")
        ReservaModel.__table__.create(connection)
        PrestamoModel.__table__.create(connection)
        RecursoModel.__table__.create(connection)
    return Session(engine, expire_on_commit=False)


def make_service(session: Session) -> ReservaService:
    return ReservaService(
        SqlReservaRepository(session),
        PrestamoService(
            prestamo_repository=SqlPrestamoRepository(session),
            checklist_repository=None,
            garantia_repository=None,
            recurso_repository=SqlRecursoRepository(session),
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
    session.add(
        RecursoModel(
            id=recurso_id,
            nombre="Proyector",
            descripcion="Proyector para aula",
            categoria="Multimedia",
            estado=EstadoRecurso.DISPONIBLE,
            marca="Epson",
            modelo="EB-X",
            numero_serie=f"SER-{recurso_id}",
            color="Blanco",
            estado_fisico="Bueno",
            foto_url="https://example.test/proyector.jpg",
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
    recurso = SqlRecursoRepository(session).obtener_por_id(recurso_id)
    assert recurso is not None
    assert recurso.estado == EstadoRecurso.EN_USO


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


def test_obtener_todas_ordena_por_fecha_inicio_e_id():
    session = make_session()
    repo = SqlReservaRepository(session)
    usuario1_id = uuid4()
    usuario2_id = uuid4()
    recurso_id = uuid4()

    id_menor = UUID("00000000-0000-0000-0000-000000000001")
    id_mayor = UUID("00000000-0000-0000-0000-000000000002")
    fecha_temprana = datetime(2026, 10, 5, tzinfo=UTC)
    fecha_tardia = datetime(2026, 10, 8, tzinfo=UTC)

    # Insertamos desordenado
    r1 = ReservaModel(
        id=id_mayor,
        usuario_id=usuario1_id,
        recurso_id=recurso_id,
        fecha_inicio=fecha_tardia,
        fecha_fin=datetime(2026, 10, 9, tzinfo=UTC),
        estado=EstadoReserva.CONFIRMADA,
    )
    r2 = ReservaModel(
        id=uuid4(),
        usuario_id=usuario2_id,
        recurso_id=recurso_id,
        fecha_inicio=fecha_temprana,
        fecha_fin=datetime(2026, 10, 6, tzinfo=UTC),
        estado=EstadoReserva.PENDIENTE,
    )
    r3 = ReservaModel(
        id=id_menor,
        usuario_id=usuario1_id,
        recurso_id=recurso_id,
        fecha_inicio=fecha_tardia,
        fecha_fin=datetime(2026, 10, 10, tzinfo=UTC),
        estado=EstadoReserva.CANCELADA,
    )
    session.add_all([r1, r2, r3])
    session.commit()

    resultado = repo.obtener_todas()

    assert len(resultado) == 3
    assert [r.id for r in resultado] == [r2.id, r3.id, r1.id]
    assert {r.usuario_id for r in resultado} == {usuario1_id, usuario2_id}
