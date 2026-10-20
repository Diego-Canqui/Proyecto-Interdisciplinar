from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from prestamos_recursos.contexts.prestamos.application.dto.prestamo_dto import PrestamoDTO
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo


class FakePrestamoRepository:
    def __init__(self, prestamos: list[Prestamo] | None = None) -> None:
        self.prestamos = prestamos or []
        self.saved = []

    def guardar(self, prestamo: Prestamo) -> None:
        self.saved.append(prestamo)

    def obtener_por_usuario(self, id_usuario):
        return [p for p in self.prestamos if p.usuario_id == id_usuario]


def test_consultar_historial_retorna_dtos_del_usuario():
    usuario_id = uuid4()
    otro_usuario_id = uuid4()

    p1 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 1, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )
    p2 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 10, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 15, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    p3 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=otro_usuario_id,
        fecha_inicio=datetime(2026, 10, 10, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 15, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )

    repo = FakePrestamoRepository([p1, p2, p3])
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )

    historial = service.consultar_historial(usuario_id)

    assert len(historial) == 2
    assert all(isinstance(dto, PrestamoDTO) for dto in historial)
    assert {dto.id for dto in historial} == {p1.id, p2.id}
    assert {dto.estado for dto in historial} == {EstadoPrestamo.DEVUELTO, EstadoPrestamo.ACTIVO}


def test_consultar_historial_vacio_si_usuario_no_tiene_prestamos():
    repo = FakePrestamoRepository([])
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )

    historial = service.consultar_historial(uuid4())
    assert historial == []

