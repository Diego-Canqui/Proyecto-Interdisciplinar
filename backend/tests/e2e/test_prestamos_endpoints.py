from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import UsuarioDTO
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    get_current_user,
)
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.presentation.dependencies import get_prestamo_service
from prestamos_recursos.main import app

client = TestClient(app)


class FakePrestamoRepository:
    def __init__(self, prestamos: list[Prestamo] | None = None) -> None:
        self.prestamos = prestamos or []

    def guardar(self, prestamo):
        if prestamo not in self.prestamos:
            self.prestamos.append(prestamo)

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


class FakeRecursoRepository:
    def __init__(self):
        self.estado = EstadoRecurso.EN_USO

    def actualizar_estado(self, id_recurso, estado):
        self.estado = estado


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.e2e
def test_consultar_historial_usuario_sin_prestamos():
    usuario_id = uuid4()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    response = client.get(f"/prestamos/usuarios/{usuario_id}/historial")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.e2e
def test_consultar_historial_con_prestamos():
    usuario_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=datetime(2026, 10, 20, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 25, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    response = client.get(f"/prestamos/usuarios/{usuario_id}/historial")
    assert response.status_code == 200
    datos = response.json()
    assert len(datos) == 1
    assert datos[0]["id"] == str(prestamo.id)
    assert datos[0]["usuario_id"] == str(usuario_id)
    assert datos[0]["estado"] == "ACTIVO"


@pytest.mark.e2e
def test_ciclo_entrega_endpoints_completo():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime(2026, 10, 30, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    prestamo_repository = FakePrestamoRepository([prestamo])
    checklist_repository = FakeChecklistRepository()
    garantia_repository = FakeGarantiaRepository()
    recurso_repository = FakeRecursoRepository()
    service = PrestamoService(
        prestamo_repository=prestamo_repository,
        checklist_repository=checklist_repository,
        garantia_repository=garantia_repository,
        recurso_repository=recurso_repository,
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    base = f"/prestamos/{prestamo.id}/entrega"
    iniciar = client.post(
        f"{base}/iniciar",
        json={
            "tipo_garantia": TipoGarantia.CARNET_UNIVERSITARIO.value,
            "compromiso_contenido": "Me responsabilizo",
            "compromiso_firma_url": "https://example.test/firma",
            "compromiso_testigo": "Encargado",
        },
    )
    assert iniciar.status_code == 200

    agregar_item = client.post(
        f"{base}/checklist/items",
        json={"observaciones": "Equipo en buen estado", "fotos_urls": ["foto.jpg"]},
    )
    assert agregar_item.status_code == 200
    assert client.post(f"{base}/confirmar").status_code == 200

    finalizar = client.post(f"{base}/finalizar")
    assert finalizar.status_code == 200
    assert finalizar.json()["estado"] == EstadoPrestamo.ENTREGADO.value
    checklist = checklist_repository.obtener_por_prestamo_y_tipo(
        prestamo.id, TipoChecklist.ESTADO_INICIAL
    )
    garantia = garantia_repository.obtener_por_prestamo(prestamo.id)
    assert checklist is not None and checklist.completo
    assert garantia is not None and garantia.estado == EstadoGarantia.REGISTRADA

    devolucion = client.post(f"/prestamos/{prestamo.id}/devolucion")
    assert devolucion.status_code == 200
    assert devolucion.json() == {
        "detalle": "Devolución registrada",
        "estado": EstadoPrestamo.DEVUELTO.value,
        "dias_retraso": 0,
    }
    assert prestamo.estado == EstadoPrestamo.DEVUELTO
    assert recurso_repository.estado == EstadoRecurso.DISPONIBLE
    segunda_devolucion = client.post(f"/prestamos/{prestamo.id}/devolucion")
    assert segunda_devolucion.status_code == 409
    assert segunda_devolucion.json()["detail"] == "El préstamo ya fue devuelto"


@pytest.mark.e2e
def test_devolucion_prestamo_inexistente_retorna_404():
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    response = client.post(f"/prestamos/{uuid4()}/devolucion")

    assert response.status_code == 404
    assert response.json()["detail"] == "Préstamo no encontrado"


def _crear_usuario(usuario_id, roles):
    return UsuarioDTO(
        id=usuario_id,
        nombre="Usuario Test",
        correo="test@example.com",
        telefono=None,
        roles=roles,
        estado=True,
    )


@pytest.mark.e2e
def test_listar_todos_prestamos_con_gestor_almacen_retorna_200():
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
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([p1, p2]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    response = client.get("/prestamos")

    assert response.status_code == 200
    datos = response.json()
    assert len(datos) == 2
    ids_recibidos = {item["id"] for item in datos}
    assert ids_recibidos == {str(p1.id), str(p2.id)}


@pytest.mark.e2e
def test_listar_todos_prestamos_con_administrador_sistema_retorna_200():
    p1 = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 10, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 15, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([p1]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ADMINISTRADOR_SISTEMA]
    )

    response = client.get("/prestamos")

    assert response.status_code == 200
    datos = response.json()
    assert len(datos) == 1
    assert datos[0]["id"] == str(p1.id)


@pytest.mark.e2e
def test_listar_todos_prestamos_con_estudiante_retorna_403():
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ESTUDIANTE]
    )

    response = client.get("/prestamos")

    assert response.status_code == 403


@pytest.mark.e2e
def test_listar_todos_prestamos_sin_token_retorna_401():
    response = client.get("/prestamos")

    assert response.status_code == 401


