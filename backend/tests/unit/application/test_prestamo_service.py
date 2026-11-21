from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.prestamos.application.dto.prestamo_dto import PrestamoDTO
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.entities.garantia import Garantia
from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_dano_devolucion import (
    TipoDanoDevolucion,
)
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.domain.value_objects.compromiso_responsabilidad import (
    CompromisoResponsabilidad,
)


class FakeRecursoRepository:
    def __init__(
        self,
        estado_inicial: EstadoRecurso = EstadoRecurso.EN_USO,
        nombre: str | None = None,
    ) -> None:
        self.estado = estado_inicial
        self.nombre = nombre
        self.actualizaciones: list[tuple] = []

    def obtener_por_id(self, id_recurso):
        return SimpleNamespace(id=id_recurso, estado=self.estado, nombre=self.nombre)

    def actualizar_estado(self, id_recurso, estado: EstadoRecurso) -> None:
        self.actualizaciones.append((id_recurso, estado))
        self.estado = estado



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
        fecha_inicio=datetime.now(UTC) + timedelta(days=1),
        fecha_fin=datetime.now(UTC) + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    p3 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=otro_usuario_id,
        fecha_inicio=datetime.now(UTC) + timedelta(days=1),
        fecha_fin=datetime.now(UTC) + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
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
    assert {dto.estado for dto in historial} == {
        EstadoPrestamo.DEVUELTO,
        EstadoPrestamo.POR_ENTREGAR,
    }


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
        fecha_inicio=datetime.now(UTC) - timedelta(days=2),
        fecha_fin=datetime.now(UTC) + timedelta(days=5),
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
        fecha_fin=datetime.now(UTC) + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
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
        fecha_inicio=datetime.now(UTC) + timedelta(days=1),
        fecha_fin=datetime.now(UTC) + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
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
    assert {dto.estado for dto in resultado} == {
        EstadoPrestamo.DEVUELTO,
        EstadoPrestamo.POR_ENTREGAR,
    }


def test_consultar_todos_retorna_lista_vacia_cuando_no_hay_prestamos():
    repo = FakePrestamoRepository([])
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )

    resultado = service.consultar_todos()

    assert resultado == []


def test_cancelar_prestamo_por_entregar_exitoso_y_libera_recurso():
    usuario_id = uuid4()
    recurso_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC) + timedelta(days=3),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    repo = FakePrestamoRepository([prestamo])
    recurso_repo = FakeRecursoRepository(estado_inicial=EstadoRecurso.EN_USO)
    reputacion_mock = SimpleNamespace()
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
        recurso_repository=recurso_repo,
        reputacion_service=reputacion_mock,
    )

    dto = service.cancelar_prestamo(prestamo.id, motivo="Cancelado por usuario")

    assert dto.id == prestamo.id
    assert dto.estado == EstadoPrestamo.CANCELADO
    assert prestamo.estado == EstadoPrestamo.CANCELADO
    assert repo.saved == [prestamo]
    assert recurso_repo.estado == EstadoRecurso.DISPONIBLE
    assert recurso_repo.actualizaciones == [(recurso_id, EstadoRecurso.DISPONIBLE)]


def test_cancelar_prestamo_inexistente_lanza_error():
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )

    with pytest.raises(ValueError, match="Préstamo no encontrado"):
        service.cancelar_prestamo(uuid4())


def test_cancelar_prestamo_no_activo_lanza_error():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC) + timedelta(days=3),
        estado=EstadoPrestamo.ENTREGADO,
    )
    repo = FakePrestamoRepository([prestamo])
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )

    with pytest.raises(
        ValueError, match="Solo se pueden cancelar préstamos pendientes de entrega física"
    ):
        service.cancelar_prestamo(prestamo.id)


def test_contar_prestamos_en_curso():
    usuario_id = uuid4()
    otro_usuario_id = uuid4()

    p_por_entregar = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC) + timedelta(days=1),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    p_entregado = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime.now(UTC) - timedelta(days=2),
        fecha_fin=datetime.now(UTC) + timedelta(days=2),
        estado=EstadoPrestamo.ENTREGADO,
    )
    p_vencido = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime.now(UTC) - timedelta(days=5),
        fecha_fin=datetime.now(UTC) - timedelta(days=1),
        estado=EstadoPrestamo.VENCIDO,
    )
    p_devuelto = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime.now(UTC) - timedelta(days=5),
        fecha_fin=datetime.now(UTC) - timedelta(days=1),
        estado=EstadoPrestamo.DEVUELTO,
    )
    p_cancelado = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC) + timedelta(days=1),
        estado=EstadoPrestamo.CANCELADO,
    )
    p_otro = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=otro_usuario_id,
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC) + timedelta(days=1),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )

    repo = FakePrestamoRepository(
        [p_por_entregar, p_entregado, p_vencido, p_devuelto, p_cancelado, p_otro]
    )
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )

    conteo = service.contar_prestamos_en_curso(usuario_id)
    assert conteo == 3


def test_procesar_devolucion_sin_danos_libera_garantia():
    recurso_id = uuid4()
    prestamo_id = uuid4()
    prestamo = Prestamo(
        id=prestamo_id,
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=uuid4(),
        fecha_inicio=datetime.now(UTC) - timedelta(days=2),
        fecha_fin=datetime.now(UTC) + timedelta(days=2),
        estado=EstadoPrestamo.ENTREGADO,
    )
    fecha_reg = datetime.now(UTC) - timedelta(days=2)
    garantia = Garantia(
        prestamo_id=prestamo_id,
        tipo=TipoGarantia.CARNET_UNIVERSITARIO,
        estado=EstadoGarantia.REGISTRADA,
        fecha_registro=fecha_reg,
        compromiso=CompromisoResponsabilidad(
            contenido="Compromiso",
            fecha_firma=fecha_reg,
            firma_url="https://example.com/firma.png",
            testigo="Operador",
        ),
    )
    prestamo_repo = FakePrestamoRepository([prestamo])
    garantia_repo = FakeGarantiaRepository()
    garantia_repo.guardar(garantia)
    checklist_repo = FakeChecklistRepository()
    recurso_repo = FakeRecursoRepository()

    service = PrestamoService(
        prestamo_repository=prestamo_repo,
        checklist_repository=checklist_repo,
        garantia_repository=garantia_repo,
        recurso_repository=recurso_repo,
    )

    dias = service.procesar_devolucion(prestamo_id, danos_detectados=False)
    assert dias == 0
    assert garantia.estado == EstadoGarantia.LIBERADA
    assert garantia.fecha_liberacion is not None

    inspecciones = service.consultar_inspecciones(prestamo_id)
    assert inspecciones["garantia"] is not None
    assert inspecciones["garantia"]["estado"] == EstadoGarantia.LIBERADA.value
    assert inspecciones["garantia"]["fecha_liberacion"] == garantia.fecha_liberacion


def test_procesar_devolucion_con_danos_retiene_garantia():
    recurso_id = uuid4()
    prestamo_id = uuid4()
    prestamo = Prestamo(
        id=prestamo_id,
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=uuid4(),
        fecha_inicio=datetime.now(UTC) - timedelta(days=2),
        fecha_fin=datetime.now(UTC) + timedelta(days=2),
        estado=EstadoPrestamo.ENTREGADO,
    )
    fecha_reg = datetime.now(UTC) - timedelta(days=2)
    garantia = Garantia(
        prestamo_id=prestamo_id,
        tipo=TipoGarantia.CARNET_UNIVERSITARIO,
        estado=EstadoGarantia.REGISTRADA,
        fecha_registro=fecha_reg,
        compromiso=CompromisoResponsabilidad(
            contenido="Compromiso",
            fecha_firma=fecha_reg,
            firma_url="https://example.com/firma.png",
            testigo="Operador",
        ),
    )
    prestamo_repo = FakePrestamoRepository([prestamo])
    garantia_repo = FakeGarantiaRepository()
    garantia_repo.guardar(garantia)
    checklist_repo = FakeChecklistRepository()
    recurso_repo = FakeRecursoRepository()

    service = PrestamoService(
        prestamo_repository=prestamo_repo,
        checklist_repository=checklist_repo,
        garantia_repository=garantia_repo,
        recurso_repository=recurso_repo,
    )

    dias = service.procesar_devolucion(
        prestamo_id, observaciones_retorno="Pantalla rota", danos_detectados=True
    )
    assert dias == 0
    assert garantia.estado == EstadoGarantia.RETENIDA
    assert garantia.fecha_liberacion is None

    inspecciones = service.consultar_inspecciones(prestamo_id)
    assert inspecciones["garantia"] is not None
    assert inspecciones["garantia"]["estado"] == EstadoGarantia.RETENIDA.value
    assert inspecciones["garantia"]["fecha_liberacion"] is None


def test_obtener_prestamo_retorna_dto_o_none():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime.now(UTC) + timedelta(days=1),
        fecha_fin=datetime.now(UTC) + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    repo = FakePrestamoRepository([prestamo])
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
    )

    dto = service.obtener_prestamo(prestamo.id)
    assert dto is not None
    assert isinstance(dto, PrestamoDTO)
    assert dto.id == prestamo.id
    assert dto.fecha_entrega_real is None
    assert dto.fecha_devolucion_real is None

    assert service.obtener_prestamo(uuid4()) is None


def test_completar_entrega_y_devolucion_registran_fechas_reales():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime.now(UTC) - timedelta(minutes=10),
        fecha_fin=datetime.now(UTC) + timedelta(days=2),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    repo = FakePrestamoRepository([prestamo])
    checklist_repo = FakeChecklistRepository()
    garantia_repo = FakeGarantiaRepository()
    recurso_repo = FakeRecursoRepository()
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=checklist_repo,
        garantia_repository=garantia_repo,
        recurso_repository=recurso_repo,
    )

    compromiso = CompromisoResponsabilidad(
        contenido="Compromiso firmado",
        fecha_firma=datetime.now(UTC),
        firma_url="https://example.com/firma.png",
        testigo="Operador",
    )
    service.completar_entrega(
        prestamo.id,
        TipoGarantia.CARNET_UNIVERSITARIO,
        compromiso,
        observaciones_checklist="Equipo completo",
    )

    dto_entregado = service.obtener_prestamo(prestamo.id)
    assert dto_entregado is not None
    assert dto_entregado.estado == EstadoPrestamo.ENTREGADO
    assert dto_entregado.fecha_entrega_real is not None
    assert dto_entregado.fecha_devolucion_real is None

    service.procesar_devolucion(prestamo.id, observaciones_retorno="Sin novedades")
    dto_devuelto = service.obtener_prestamo(prestamo.id)
    assert dto_devuelto is not None
    assert dto_devuelto.estado == EstadoPrestamo.DEVUELTO
    assert dto_devuelto.fecha_entrega_real == dto_entregado.fecha_entrega_real
    assert dto_devuelto.fecha_devolucion_real is not None


def test_consultar_inspecciones_prestamo_inexistente_lanza_error():
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
    )

    with pytest.raises(ValueError, match="Préstamo no encontrado"):
        service.consultar_inspecciones(uuid4())


class FakeReputacionService:
    def __init__(self) -> None:
        self.sanciones: list[dict] = []
        self.premios: list = []
        self.premios_detalle: list[dict] = []

    def aplicar_sancion(
        self,
        usuario_id,
        tipo: TipoSancion,
        motivo: str,
        monto_opcional: Decimal | None = None,
        dias_retardo: int | None = None,
        prestamo_id=None,
        reserva_id=None,
        recurso_id=None,
        recurso_nombre: str | None = None,
    ) -> None:
        self.sanciones.append(
            {
                "usuario_id": usuario_id,
                "tipo": tipo,
                "motivo": motivo,
                "monto_opcional": monto_opcional,
                "dias_retardo": dias_retardo,
                "prestamo_id": prestamo_id,
                "reserva_id": reserva_id,
                "recurso_id": recurso_id,
                "recurso_nombre": recurso_nombre,
            }
        )

    def premiar_devolucion_puntual(
        self,
        usuario_id,
        prestamo_id=None,
        reserva_id=None,
        recurso_id=None,
        recurso_nombre: str | None = None,
    ) -> None:
        self.premios.append(usuario_id)
        self.premios_detalle.append(
            {
                "evento": "premiar_devolucion_puntual",
                "usuario_id": usuario_id,
                "prestamo_id": prestamo_id,
                "reserva_id": reserva_id,
                "recurso_id": recurso_id,
                "recurso_nombre": recurso_nombre,
            }
        )

    def premiar_entrega_puntual(
        self,
        usuario_id,
        prestamo_id=None,
        reserva_id=None,
        recurso_id=None,
        recurso_nombre: str | None = None,
    ) -> None:
        self.premios.append(usuario_id)
        self.premios_detalle.append(
            {
                "evento": "premiar_entrega_puntual",
                "usuario_id": usuario_id,
                "prestamo_id": prestamo_id,
                "reserva_id": reserva_id,
                "recurso_id": recurso_id,
                "recurso_nombre": recurso_nombre,
            }
        )


def test_obtener_plantilla_checklist_por_categoria_y_respaldo_generico():
    recurso_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=uuid4(),
        fecha_inicio=datetime.now(UTC) + timedelta(days=1),
        fecha_fin=datetime.now(UTC) + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    repo = FakePrestamoRepository([prestamo])

    recurso_repo_libros = SimpleNamespace(
        obtener_por_id=lambda _id: SimpleNamespace(id=recurso_id, categoria="Libros")
    )
    service_libros = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        catalogo_service=recurso_repo_libros,
    )
    plantilla = service_libros.obtener_plantilla_checklist(prestamo.id)
    assert plantilla["prestamo_id"] == prestamo.id
    assert plantilla["recurso_id"] == recurso_id
    assert plantilla["categoria"] == "Libros"
    assert any(item["id"] == "paginas" for item in plantilla["items"])

    # Con catalogo_service=None o obtener_por_id() -> None, cae a genérica sin AttributeError
    service_sin_catalogo = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
    )
    plantilla_gen = service_sin_catalogo.obtener_plantilla_checklist(prestamo.id)
    assert plantilla_gen["categoria"] == ""
    assert any(item["id"] == "estado_general" for item in plantilla_gen["items"])

    service_recurso_none = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        catalogo_service=SimpleNamespace(obtener_por_id=lambda _id: None),
    )
    plantilla_none = service_recurso_none.obtener_plantilla_checklist(prestamo.id)
    assert plantilla_none["categoria"] == ""
    assert any(item["id"] == "estado_general" for item in plantilla_none["items"])

    with pytest.raises(ValueError, match="Préstamo no encontrado"):
        service_libros.obtener_plantilla_checklist(uuid4())


def test_procesar_devolucion_dano_parcial():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    garantia = Garantia(
        prestamo_id=prestamo.id,
        tipo=TipoGarantia.CARNET_UNIVERSITARIO,
        estado=EstadoGarantia.REGISTRADA,
        fecha_registro=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        compromiso=CompromisoResponsabilidad(
            contenido="Compromiso",
            fecha_firma=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
            firma_url="https://example.com/firma.png",
            testigo="Operador",
        ),
    )
    garantia_repo = FakeGarantiaRepository()
    garantia_repo.guardar(garantia)
    recurso_repo = FakeRecursoRepository()
    reputacion = FakeReputacionService()

    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=garantia_repo,
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )

    resultado = service.procesar_devolucion_detallada(
        prestamo.id,
        observaciones_retorno="Teclado dañado",
        tipo_dano=TipoDanoDevolucion.DANO_PARCIAL,
        fecha_devolucion=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
    )

    assert resultado["dias_retraso"] == 0
    assert resultado["puntual"] is True
    assert resultado["tipo_dano"] == TipoDanoDevolucion.DANO_PARCIAL.value
    assert garantia.estado == EstadoGarantia.RETENIDA
    assert recurso_repo.estado == EstadoRecurso.MANTENIMIENTO
    assert len(reputacion.sanciones) == 1
    assert reputacion.sanciones[0]["tipo"] == TipoSancion.DANO_PARCIAL
    assert reputacion.premios == []


def test_procesar_devolucion_dano_total_con_monto_valido():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    garantia = Garantia(
        prestamo_id=prestamo.id,
        tipo=TipoGarantia.CARNET_UNIVERSITARIO,
        estado=EstadoGarantia.REGISTRADA,
        fecha_registro=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        compromiso=CompromisoResponsabilidad(
            contenido="Compromiso",
            fecha_firma=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
            firma_url="https://example.com/firma.png",
            testigo="Operador",
        ),
    )
    garantia_repo = FakeGarantiaRepository()
    garantia_repo.guardar(garantia)
    recurso_repo = FakeRecursoRepository()
    reputacion = FakeReputacionService()

    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=garantia_repo,
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )

    resultado = service.procesar_devolucion_detallada(
        prestamo.id,
        observaciones_retorno="Equipo destruido",
        tipo_dano=TipoDanoDevolucion.DANO_TOTAL,
        monto_dano=Decimal("450.00"),
        fecha_devolucion=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
    )

    assert resultado["tipo_dano"] == TipoDanoDevolucion.DANO_TOTAL.value
    assert garantia.estado == EstadoGarantia.RETENIDA
    assert recurso_repo.estado == EstadoRecurso.FUERA_DE_SERVICIO
    assert len(reputacion.sanciones) == 1
    assert reputacion.sanciones[0]["tipo"] == TipoSancion.DANO_TOTAL
    assert reputacion.sanciones[0]["monto_opcional"] == Decimal("450.00")
    assert reputacion.premios == []


@pytest.mark.parametrize("monto_invalido", [None, Decimal("0"), Decimal("-15")])
def test_procesar_devolucion_dano_total_sin_monto_lanza_error_sin_mutar(monto_invalido):
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    recurso_repo = FakeRecursoRepository()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        recurso_repository=recurso_repo,
    )

    with pytest.raises(ValueError, match="monto mayor a cero"):
        service.procesar_devolucion_detallada(
            prestamo.id,
            tipo_dano=TipoDanoDevolucion.DANO_TOTAL,
            monto_dano=monto_invalido,
        )

    assert prestamo.estado == EstadoPrestamo.ENTREGADO
    assert recurso_repo.estado == EstadoRecurso.EN_USO


def test_procesar_devolucion_mismo_dia_tarde_no_sanciona_ni_premia_puntualidad():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 5, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, 14, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=FakeRecursoRepository(),
    )

    resultado = service.procesar_devolucion_detallada(
        prestamo.id,
        fecha_devolucion=datetime(2026, 10, 5, 16, 0, tzinfo=UTC),
    )

    assert resultado["dias_retraso"] == 0
    assert resultado["puntual"] is False
    assert reputacion.sanciones == []
    assert reputacion.premios == []


def test_procesar_devolucion_puntual_sin_danos_premia_reputacion():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 5, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, 14, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=FakeRecursoRepository(),
    )

    resultado = service.procesar_devolucion_detallada(
        prestamo.id,
        fecha_devolucion=datetime(2026, 10, 5, 14, 0, tzinfo=UTC),
    )

    assert resultado["dias_retraso"] == 0
    assert resultado["puntual"] is True
    assert reputacion.sanciones == []
    assert reputacion.premios == [prestamo.usuario_id]


def _fijar_ahora(monkeypatch, instante: datetime) -> None:
    class _FakeDatetime:
        @staticmethod
        def now(_tz=None):
            return instante

    monkeypatch.setattr(
        "prestamos_recursos.contexts.prestamos.application.prestamo_service.datetime",
        _FakeDatetime,
    )


def test_prestamo_service_no_expone_renovar_prestamo():
    assert not hasattr(PrestamoService, "renovar_prestamo")


def test_solicitar_prestamo_crea_en_estado_por_entregar_y_ocupa_recurso():
    recurso_id = uuid4()
    repo = FakePrestamoRepository()
    recurso_repo = FakeRecursoRepository(estado_inicial=EstadoRecurso.DISPONIBLE)
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        recurso_repository=recurso_repo,
    )

    creado = service.solicitar_prestamo(
        id_reserva=uuid4(),
        id_usuario=uuid4(),
        id_recurso=recurso_id,
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
    )

    assert creado is True
    assert len(repo.saved) == 1
    assert repo.saved[0].estado == EstadoPrestamo.POR_ENTREGAR
    assert recurso_repo.estado == EstadoRecurso.EN_USO


def test_sincronizacion_por_entregar_respeta_limite_30_min_y_expira_despues(monkeypatch):
    usuario_id = uuid4()
    recurso_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    repo = FakePrestamoRepository([prestamo])
    recurso_repo = FakeRecursoRepository(estado_inicial=EstadoRecurso.EN_USO)
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )

    # CL-1: 10:30 exactas aún dentro del límite
    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 30, tzinfo=UTC))
    dto_en_limite = service.obtener_prestamo(prestamo.id)
    assert dto_en_limite is not None
    assert dto_en_limite.estado == EstadoPrestamo.POR_ENTREGAR
    assert recurso_repo.estado == EstadoRecurso.EN_USO
    assert reputacion.sanciones == []

    # CL-1: 10:31 expira automáticamente
    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 31, tzinfo=UTC))
    dto_expirado = service.obtener_prestamo(prestamo.id)
    assert dto_expirado is not None
    assert dto_expirado.estado == EstadoPrestamo.CANCELADO
    assert recurso_repo.estado == EstadoRecurso.DISPONIBLE
    assert recurso_repo.actualizaciones == [(recurso_id, EstadoRecurso.DISPONIBLE)]
    assert len(reputacion.sanciones) == 1
    assert reputacion.sanciones[0]["usuario_id"] == usuario_id
    assert reputacion.sanciones[0]["tipo"] == TipoSancion.INASISTENCIA_RESERVA


def test_sincronizacion_por_entregar_ventana_corta_usa_fecha_fin_como_limite(monkeypatch):
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 10, 20, tzinfo=UTC),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=FakeReputacionService(),
        recurso_repository=FakeRecursoRepository(),
    )

    # CL-2: a las 10:20 exactas no expira
    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 20, tzinfo=UTC))
    assert service.consultar_todos()[0].estado == EstadoPrestamo.POR_ENTREGAR

    # CL-2: a las 10:21 expira
    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 21, tzinfo=UTC))
    assert service.consultar_todos()[0].estado == EstadoPrestamo.CANCELADO


def test_sincronizacion_por_entregar_delega_sancion_inasistencia_a_reputacion(monkeypatch):
    # CL-3: PrestamoService delega aplicar_sancion(INASISTENCIA_RESERVA) a ReputacionService,
    # que respeta excepciones académicas vigentes al registrar la sanción.
    usuario_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=FakeRecursoRepository(),
    )

    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 31, tzinfo=UTC))
    service.consultar_historial(usuario_id)

    assert len(reputacion.sanciones) == 1
    assert reputacion.sanciones[0]["usuario_id"] == usuario_id
    assert reputacion.sanciones[0]["tipo"] == TipoSancion.INASISTENCIA_RESERVA


def test_sincronizacion_es_idempotente_en_consultas_repetidas(monkeypatch):
    # CL-4: una segunda consulta no vuelve a liberar recurso ni duplicar sanción.
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    recurso_repo = FakeRecursoRepository(estado_inicial=EstadoRecurso.EN_USO)
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )

    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 31, tzinfo=UTC))
    service.consultar_todos()
    service.consultar_todos()
    service.obtener_prestamo(prestamo.id)

    assert prestamo.estado == EstadoPrestamo.CANCELADO
    assert len(recurso_repo.actualizaciones) == 1
    assert len(reputacion.sanciones) == 1


@pytest.mark.parametrize(
    "estado_recurso",
    [EstadoRecurso.MANTENIMIENTO, EstadoRecurso.FUERA_DE_SERVICIO],
)
def test_sincronizacion_no_sobrescribe_recurso_en_mantenimiento_o_fuera_de_servicio(
    monkeypatch, estado_recurso
):
    # CL-11: si el recurso está en MANTENIMIENTO o FUERA_DE_SERVICIO, no pasa a DISPONIBLE.
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    recurso_repo = FakeRecursoRepository(estado_inicial=estado_recurso)
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )

    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 31, tzinfo=UTC))
    dto = service.obtener_prestamo(prestamo.id)

    assert dto is not None
    assert dto.estado == EstadoPrestamo.CANCELADO
    assert recurso_repo.estado == estado_recurso
    assert recurso_repo.actualizaciones == []
    assert len(reputacion.sanciones) == 1


def test_sincronizacion_entregado_pasa_a_vencido_y_devolucion_mismo_dia(monkeypatch):
    # CL-5: ENTREGADO a las 14:00 sigue ENTREGADO; a las 14:01 pasa a VENCIDO.
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 11, 20, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 14, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=FakeRecursoRepository(),
    )

    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 14, 0, tzinfo=UTC))
    assert service.obtener_prestamo(prestamo.id).estado == EstadoPrestamo.ENTREGADO

    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 14, 1, tzinfo=UTC))
    assert service.obtener_prestamo(prestamo.id).estado == EstadoPrestamo.VENCIDO

    resultado = service.procesar_devolucion_detallada(
        prestamo.id,
        fecha_devolucion=datetime(2026, 11, 20, 16, 0, tzinfo=UTC),
    )
    assert prestamo.estado == EstadoPrestamo.DEVUELTO
    assert resultado["dias_retraso"] == 0
    assert resultado["puntual"] is False
    assert reputacion.sanciones == []
    assert reputacion.premios == []


def test_sincronizacion_en_inspecciones_y_conteo_en_curso(monkeypatch):
    usuario_id = uuid4()
    p_expirado = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    p_vencido = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 11, 20, 8, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([p_expirado, p_vencido]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=FakeRecursoRepository(),
    )

    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 31, tzinfo=UTC))
    inspecciones = service.consultar_inspecciones(p_expirado.id)
    assert inspecciones["prestamo_id"] == p_expirado.id
    assert p_expirado.estado == EstadoPrestamo.CANCELADO

    conteo = service.contar_prestamos_en_curso(usuario_id)
    assert conteo == 1
    assert p_vencido.estado == EstadoPrestamo.VENCIDO
    assert len(reputacion.sanciones) == 1


@pytest.mark.parametrize("operacion", ["iniciar", "agregar_item", "confirmar", "finalizar", "cancelar"])
def test_mutaciones_sobre_por_entregar_expirado_persisten_y_rechazan(monkeypatch, operacion):
    # CL-9: al intentar mutar un POR_ENTREGAR ya expirado, primero persiste CANCELADO + sanción
    # y luego rechaza la mutación con ValueError.
    recurso_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    repo = FakePrestamoRepository([prestamo])
    recurso_repo = FakeRecursoRepository(estado_inicial=EstadoRecurso.EN_USO)
    reputacion = FakeReputacionService()
    service = PrestamoService(
        prestamo_repository=repo,
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )
    compromiso = CompromisoResponsabilidad(
        contenido="Compromiso",
        fecha_firma=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        firma_url="https://example.test/firma",
        testigo="Encargado",
    )

    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 31, tzinfo=UTC))
    with pytest.raises(ValueError):
        if operacion == "iniciar":
            service.iniciar_entrega(prestamo.id, TipoGarantia.CARNET_UNIVERSITARIO, compromiso)
        elif operacion == "agregar_item":
            service.agregar_item_checklist(prestamo.id, "Obs", [])
        elif operacion == "confirmar":
            service.confirmar_entrega(prestamo.id)
        elif operacion == "finalizar":
            service.finalizar_entrega(prestamo.id)
        else:
            service.cancelar_prestamo(prestamo.id, motivo="Tarde")

    assert prestamo.estado == EstadoPrestamo.CANCELADO
    assert prestamo in repo.saved
    assert recurso_repo.estado == EstadoRecurso.DISPONIBLE
    assert len(reputacion.sanciones) == 1


def test_finalizar_entrega_puntual_propaga_referencias_y_nombre_recurso():
    usuario_id = uuid4()
    recurso_id = uuid4()
    reserva_id = uuid4()
    prestamo = Prestamo(
        reserva_id=reserva_id,
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC) + timedelta(days=3),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    reputacion = FakeReputacionService()
    recurso_repo = FakeRecursoRepository(
        estado_inicial=EstadoRecurso.EN_USO,
        nombre="Osciloscopio Tektronix",
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )
    compromiso = CompromisoResponsabilidad(
        contenido="Compromiso",
        fecha_firma=datetime.now(UTC),
        firma_url="https://example.test/firma",
        testigo="Encargado",
    )

    service.completar_entrega(
        prestamo.id,
        TipoGarantia.CARNET_UNIVERSITARIO,
        compromiso,
        observaciones_checklist="Sin novedades",
    )

    assert reputacion.premios_detalle == [
        {
            "evento": "premiar_entrega_puntual",
            "usuario_id": usuario_id,
            "prestamo_id": prestamo.id,
            "reserva_id": reserva_id,
            "recurso_id": recurso_id,
            "recurso_nombre": "Osciloscopio Tektronix",
        }
    ]


def test_sincronizacion_por_entregar_expirado_propaga_referencias_y_nombre_recurso(monkeypatch):
    usuario_id = uuid4()
    recurso_id = uuid4()
    reserva_id = uuid4()
    prestamo = Prestamo(
        reserva_id=reserva_id,
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 11, 20, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    reputacion = FakeReputacionService()
    recurso_repo = FakeRecursoRepository(
        estado_inicial=EstadoRecurso.EN_USO,
        nombre="Proyector Epson",
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )

    _fijar_ahora(monkeypatch, datetime(2026, 11, 20, 10, 31, tzinfo=UTC))
    dto = service.obtener_prestamo(prestamo.id)

    assert dto is not None and dto.estado == EstadoPrestamo.CANCELADO
    assert len(reputacion.sanciones) == 1
    assert reputacion.sanciones[0]["tipo"] == TipoSancion.INASISTENCIA_RESERVA
    assert reputacion.sanciones[0]["prestamo_id"] == prestamo.id
    assert reputacion.sanciones[0]["reserva_id"] == reserva_id
    assert reputacion.sanciones[0]["recurso_id"] == recurso_id
    assert reputacion.sanciones[0]["recurso_nombre"] == "Proyector Epson"


def test_procesar_devolucion_puntual_propaga_referencias_y_nombre_recurso():
    usuario_id = uuid4()
    recurso_id = uuid4()
    reserva_id = uuid4()
    prestamo = Prestamo(
        reserva_id=reserva_id,
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 5, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, 14, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    reputacion = FakeReputacionService()
    recurso_repo = FakeRecursoRepository(nombre="Cámara Sony Alpha")
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )

    resultado = service.procesar_devolucion_detallada(
        prestamo.id,
        fecha_devolucion=datetime(2026, 10, 5, 14, 0, tzinfo=UTC),
    )

    assert resultado["puntual"] is True
    assert reputacion.premios_detalle == [
        {
            "evento": "premiar_devolucion_puntual",
            "usuario_id": usuario_id,
            "prestamo_id": prestamo.id,
            "reserva_id": reserva_id,
            "recurso_id": recurso_id,
            "recurso_nombre": "Cámara Sony Alpha",
        }
    ]


@pytest.mark.parametrize(
    ("tipo_dano", "monto_dano", "sancion_dano"),
    [
        (TipoDanoDevolucion.DANO_PARCIAL, None, TipoSancion.DANO_PARCIAL),
        (TipoDanoDevolucion.DANO_TOTAL, Decimal("320.00"), TipoSancion.DANO_TOTAL),
    ],
)
def test_procesar_devolucion_dano_y_tardanza_simultaneos_ordena_dano_luego_tardanza(
    tipo_dano, monto_dano, sancion_dano
):
    usuario_id = uuid4()
    recurso_id = uuid4()
    reserva_id = uuid4()
    prestamo = Prestamo(
        reserva_id=reserva_id,
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    reputacion = FakeReputacionService()
    recurso_repo = FakeRecursoRepository(nombre="Multímetro Fluke")
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=reputacion,
        recurso_repository=recurso_repo,
    )

    resultado = service.procesar_devolucion_detallada(
        prestamo.id,
        observaciones_retorno="Con golpe en carcasa",
        tipo_dano=tipo_dano,
        monto_dano=monto_dano,
        fecha_devolucion=datetime(2026, 10, 7, 19, 0, tzinfo=UTC),
    )

    assert resultado["dias_retraso"] == 2
    assert len(reputacion.sanciones) == 2
    assert [s["tipo"] for s in reputacion.sanciones] == [sancion_dano, TipoSancion.TARDANZA]
    assert reputacion.sanciones[0]["monto_opcional"] == monto_dano
    assert reputacion.sanciones[1]["dias_retardo"] == 2
    for sancion in reputacion.sanciones:
        assert sancion["prestamo_id"] == prestamo.id
        assert sancion["reserva_id"] == reserva_id
        assert sancion["recurso_id"] == recurso_id
        assert sancion["recurso_nombre"] == "Multímetro Fluke"


def test_resolver_nombre_recurso_y_doble_reputacion_sin_kwargs_extra():
    usuario_id = uuid4()
    recurso_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )

    class CatalogoQueFalla:
        def obtener_por_id(self, _id):
            raise RuntimeError("Fallo temporal en catálogo")

        def actualizar_estado(self, _id, _estado):
            return None

    llamadas = []

    class ReputacionSinKwargsExtra:
        def aplicar_sancion(self, uid, tipo, motivo, dias_retardo=None):
            llamadas.append((uid, tipo, motivo, dias_retardo))

    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        reputacion_service=ReputacionSinKwargsExtra(),
        recurso_repository=CatalogoQueFalla(),
    )

    assert service._resolver_nombre_recurso(recurso_id) is None
    service.procesar_devolucion_detallada(
        prestamo.id,
        fecha_devolucion=datetime(2026, 10, 7, 19, 0, tzinfo=UTC),
    )

    assert llamadas == [(usuario_id, TipoSancion.TARDANZA, "Devolución tardía", 2)]






def test_consultar_historial_por_recurso_filtra_por_recurso():
    recurso_objetivo = uuid4()
    otro_recurso = uuid4()
    p1 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_objetivo,
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 2, 10, 0, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )
    p2 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=otro_recurso,
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 3, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 4, 10, 0, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([p1, p2]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
    )

    historial = service.consultar_historial_por_recurso(recurso_objetivo)
    assert [p.id for p in historial] == [p1.id]
