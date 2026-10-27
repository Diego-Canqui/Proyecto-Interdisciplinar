from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from prestamos_recursos.contexts.prestamos.application.dto.prestamo_dto import PrestamoDTO
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.domain.value_objects.compromiso_responsabilidad import (
    CompromisoResponsabilidad,
)


class FakePrestamoRepository:
    def __init__(self, prestamos: list[Prestamo] | None = None) -> None:
        self.prestamos = prestamos or []
        self.saved = []

    def guardar(self, prestamo: Prestamo) -> None:
        self.saved.append(prestamo)

    def obtener_por_usuario(self, id_usuario):
        return [p for p in self.prestamos if p.usuario_id == id_usuario]

    def obtener_por_id(self, id_prestamo):
        return next((p for p in self.prestamos if p.id == id_prestamo), None)

    def obtener_todos(self):
        return list(self.prestamos)


class FakeChecklistRepository:
    def __init__(self):
        self.checklists = []

    def guardar(self, checklist):
        if checklist not in self.checklists:
            self.checklists.append(checklist)

    def obtener_por_prestamo_y_tipo(self, prestamo_id, tipo):
        return next(
            (
                checklist
                for checklist in self.checklists
                if checklist.prestamo_id == prestamo_id and checklist.tipo == tipo
            ),
            None,
        )


class FakeGarantiaRepository:
    def __init__(self):
        self.garantias = []

    def guardar(self, garantia):
        if garantia not in self.garantias:
            self.garantias.append(garantia)

    def obtener_por_prestamo(self, prestamo_id):
        return next(
            (garantia for garantia in self.garantias if garantia.prestamo_id == prestamo_id),
            None,
        )


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


def test_procesar_devolucion_puntual_retorna_cero_y_premia_usuario():
    usuario_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 20, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 30, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    premiados = []
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
        reputacion_service=SimpleNamespace(
            premiar_devolucion_puntual=lambda id_usuario: premiados.append(id_usuario)
        ),
    )

    dias_retraso = service.procesar_devolucion(prestamo.id)

    assert dias_retraso == 0
    assert prestamo.estado == EstadoPrestamo.DEVUELTO
    assert premiados == [usuario_id]


def test_ciclo_entrega_completo_confirma_checklist_y_premia_puntualidad():
    usuario_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime(2026, 10, 30, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    prestamo_repository = FakePrestamoRepository([prestamo])
    checklist_repository = FakeChecklistRepository()
    garantia_repository = FakeGarantiaRepository()
    reputacion = SimpleNamespace(premiar_entrega_puntual=lambda user_id: rewarded.append(user_id))
    rewarded = []
    service = PrestamoService(
        prestamo_repository=prestamo_repository,
        checklist_repository=checklist_repository,
        garantia_repository=garantia_repository,
        reputacion_service=reputacion,
    )
    compromiso = CompromisoResponsabilidad(
        contenido="Me responsabilizo del recurso",
        fecha_firma=datetime.now(UTC),
        firma_url="https://example.test/firma",
        testigo="Encargado",
    )

    service.iniciar_entrega(prestamo.id, TipoGarantia.CARNET_UNIVERSITARIO, compromiso)
    service.agregar_item_checklist(prestamo.id, "Equipo en buen estado", ["foto.jpg"])
    service.confirmar_entrega(prestamo.id)
    service.finalizar_entrega(prestamo.id)

    checklist = checklist_repository.obtener_por_prestamo_y_tipo(
        prestamo.id, TipoChecklist.ESTADO_INICIAL
    )
    garantia = garantia_repository.obtener_por_prestamo(prestamo.id)
    assert checklist is not None and checklist.completo is True
    assert checklist.observaciones == "Equipo en buen estado"
    assert checklist.fotos_urls == ["foto.jpg"]
    assert garantia is not None and garantia.estado == EstadoGarantia.REGISTRADA
    assert prestamo.estado == EstadoPrestamo.ENTREGADO
    assert prestamo_repository.saved == [prestamo]
    assert rewarded == [usuario_id]


def test_consultar_todos_retorna_dtos_de_todos_los_prestamos():
    usuario_1 = uuid4()
    usuario_2 = uuid4()

    p1 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_1,
        fecha_inicio=datetime(2026, 10, 1, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )
    p2 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_2,
        fecha_inicio=datetime(2026, 10, 10, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 15, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )

    repo = FakePrestamoRepository([p1, p2])
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )

    resultado = service.consultar_todos()

    assert len(resultado) == 2
    assert all(isinstance(dto, PrestamoDTO) for dto in resultado)
    assert {dto.id for dto in resultado} == {p1.id, p2.id}
    assert {dto.usuario_id for dto in resultado} == {usuario_1, usuario_2}
    assert {dto.estado for dto in resultado} == {EstadoPrestamo.DEVUELTO, EstadoPrestamo.ACTIVO}


def test_consultar_todos_retorna_lista_vacia_cuando_no_hay_prestamos():
    repo = FakePrestamoRepository([])
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )

    resultado = service.consultar_todos()

    assert resultado == []


