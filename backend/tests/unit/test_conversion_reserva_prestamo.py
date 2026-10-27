from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.reservas.application.reserva_service import ReservaService
from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva


class FakeReservaRepository:
    def __init__(self, reserva):
        self.reserva = reserva
        self.saved = []

    def obtener_por_id(self, id_reserva):
        if self.reserva and self.reserva.id == id_reserva:
            return self.reserva
        return None

    def guardar(self, reserva):
        self.saved.append(reserva)


class FakePrestamoRepository:
    def __init__(self):
        self.saved = []

    def guardar(self, prestamo):
        self.saved.append(prestamo)


class FakeRecursoRepository:
    def __init__(self, estado=EstadoRecurso.DISPONIBLE, existe=True):
        self.recurso = SimpleNamespace(estado=estado) if existe else None

    def obtener_por_id(self, id_recurso):
        return self.recurso

    def actualizar_estado(self, id_recurso, estado):
        self.recurso.estado = estado


def make_reserva(estado=EstadoReserva.CONFIRMADA):
    return Reserva(
        usuario_id=uuid4(),
        recurso_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 6, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 10, 7, tzinfo=timezone.utc),
        estado=estado,
    )


def make_prestamo_service(prestamo_repository, recurso_repository=None):
    return PrestamoService(
        prestamo_repository=prestamo_repository,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
        recurso_repository=recurso_repository or FakeRecursoRepository(),
    )


def test_convertir_reserva_confirmada_crea_prestamo_activo():
    reserva = make_reserva()
    reserva_repository = FakeReservaRepository(reserva)
    prestamo_repository = FakePrestamoRepository()
    recurso_repository = FakeRecursoRepository()
    service = ReservaService(
        reserva_repository,
        make_prestamo_service(prestamo_repository, recurso_repository),
    )

    assert service.convertir_a_prestamo(reserva.id) is True

    prestamo = prestamo_repository.saved[0]
    assert prestamo.reserva_id == reserva.id
    assert prestamo.usuario_id == reserva.usuario_id
    assert prestamo.recurso_id == reserva.recurso_id
    assert prestamo.fecha_inicio == reserva.fecha_inicio
    assert prestamo.fecha_fin == reserva.fecha_fin
    assert prestamo.estado == EstadoPrestamo.ACTIVO
    assert reserva.estado == EstadoReserva.CONVERTIDA
    assert reserva_repository.saved == [reserva]
    assert recurso_repository.recurso.estado == EstadoRecurso.EN_USO


def test_convertir_reserva_no_confirmada_no_crea_prestamo():
    reserva = make_reserva(EstadoReserva.PENDIENTE)
    reserva_repository = FakeReservaRepository(reserva)
    prestamo_repository = FakePrestamoRepository()
    service = ReservaService(
        reserva_repository,
        make_prestamo_service(prestamo_repository),
    )

    assert service.convertir_a_prestamo(reserva.id) is False
    assert prestamo_repository.saved == []
    assert reserva_repository.saved == []


def test_convertir_reserva_rechaza_recurso_no_disponible():
    reserva = make_reserva()
    reserva_repository = FakeReservaRepository(reserva)
    prestamo_repository = FakePrestamoRepository()
    recurso_repository = FakeRecursoRepository(EstadoRecurso.EN_USO)
    service = ReservaService(
        reserva_repository,
        make_prestamo_service(prestamo_repository, recurso_repository),
    )

    try:
        service.convertir_a_prestamo(reserva.id)
    except ValueError as error:
        assert str(error) == "Recurso no disponible"
    else:
        raise AssertionError("Se esperaba rechazar un recurso no disponible")

    assert prestamo_repository.saved == []
    assert reserva.estado == EstadoReserva.CONFIRMADA


def test_convertir_reserva_rechaza_recurso_inexistente():
    reserva = make_reserva()
    reserva_repository = FakeReservaRepository(reserva)
    prestamo_repository = FakePrestamoRepository()
    recurso_repository = FakeRecursoRepository(existe=False)
    service = ReservaService(
        reserva_repository,
        make_prestamo_service(prestamo_repository, recurso_repository),
    )

    try:
        service.convertir_a_prestamo(reserva.id)
    except ValueError as error:
        assert str(error) == "Recurso no encontrado"
    else:
        raise AssertionError("Se esperaba rechazar un recurso inexistente")

    assert prestamo_repository.saved == []
    assert reserva.estado == EstadoReserva.CONFIRMADA