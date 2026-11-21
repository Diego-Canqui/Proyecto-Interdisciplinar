from datetime import UTC, datetime, timedelta
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
from prestamos_recursos.contexts.prestamos.domain.entities.garantia import Garantia
from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.domain.value_objects.compromiso_responsabilidad import (
    CompromisoResponsabilidad,
)
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
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        usuario_id, [RolUsuario.ESTUDIANTE]
    )

    response = client.get(f"/prestamos/usuarios/{usuario_id}/historial")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.e2e
def test_consultar_historial_con_prestamos():
    usuario_id = uuid4()
    ahora = datetime.now(UTC)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=usuario_id,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        usuario_id, [RolUsuario.ESTUDIANTE]
    )

    response = client.get(f"/prestamos/usuarios/{usuario_id}/historial")
    assert response.status_code == 200
    datos = response.json()
    assert len(datos) == 1
    assert datos[0]["id"] == str(prestamo.id)
    assert datos[0]["usuario_id"] == str(usuario_id)
    assert datos[0]["estado"] == "POR_ENTREGAR"
    assert datos[0]["fecha_entrega_real"] is None
    assert datos[0]["fecha_devolucion_real"] is None


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
def test_ciclo_entrega_endpoints_completo():
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC) + timedelta(days=7),
        estado=EstadoPrestamo.POR_ENTREGAR,
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
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

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

    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )
    devolucion = client.post(f"/prestamos/{prestamo.id}/devolucion")
    assert devolucion.status_code == 200
    assert devolucion.json() == {
        "detalle": "Devolución registrada",
        "estado": EstadoPrestamo.DEVUELTO.value,
        "dias_retraso": 0,
        "puntual": True,
        "tipo_dano": "NINGUNO",
    }
    assert prestamo.estado == EstadoPrestamo.DEVUELTO
    assert recurso_repository.estado == EstadoRecurso.DISPONIBLE

    # RF-05: verificar que la garantía quedó LIBERADA con fecha_liberacion
    res_insp_post = client.get(f"/prestamos/{prestamo.id}/inspeccion")
    assert res_insp_post.status_code == 200
    insp_post_data = res_insp_post.json()
    assert insp_post_data["garantia"]["estado"] == "LIBERADA"
    assert insp_post_data["garantia"]["fecha_liberacion"] is not None

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
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    response = client.post(f"/prestamos/{uuid4()}/devolucion")

    assert response.status_code == 404
    assert response.json()["detail"] == "Préstamo no encontrado"


@pytest.mark.e2e
def test_devolucion_con_estudiante_retorna_403():
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ESTUDIANTE]
    )

    response = client.post(f"/prestamos/{uuid4()}/devolucion")

    assert response.status_code == 403


@pytest.mark.e2e
def test_devolucion_sin_token_retorna_401():
    response = client.post(f"/prestamos/{uuid4()}/devolucion")

    assert response.status_code == 401


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
        estado=EstadoPrestamo.POR_ENTREGAR,
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
        estado=EstadoPrestamo.POR_ENTREGAR,
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


@pytest.mark.e2e
def test_endpoint_renovar_no_existe():
    ahora = datetime.now(UTC)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=5),
        estado=EstadoPrestamo.ENTREGADO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        prestamo.usuario_id, [RolUsuario.ESTUDIANTE]
    )

    response = client.post(f"/prestamos/{prestamo.id}/renovar")
    assert response.status_code in (404, 405)


@pytest.mark.e2e
def test_completar_entrega_unificada():
    ahora = datetime.now(UTC)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    prestamo_repository = FakePrestamoRepository([prestamo])
    checklist_repository = FakeChecklistRepository()
    garantia_repository = FakeGarantiaRepository()
    service = PrestamoService(
        prestamo_repository=prestamo_repository,
        checklist_repository=checklist_repository,
        garantia_repository=garantia_repository,
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    res = client.post(
        f"/prestamos/{prestamo.id}/entrega/completar",
        json={
            "tipo_garantia": "CARNET_UNIVERSITARIO",
            "compromiso_contenido": "Compromiso de entrega de equipo",
            "compromiso_firma_url": "https://example.com/firma.png",
            "compromiso_testigo": "Operador Almacén",
            "observaciones_checklist": "Pantalla sin arañazos, cable y cargador incluidos",
            "fotos_urls": ["https://example.com/foto1.jpg"],
        },
    )
    assert res.status_code == 200
    assert res.json()["estado"] == "ENTREGADO"
    assert prestamo.estado == EstadoPrestamo.ENTREGADO

    # Consultar inspección
    res_insp = client.get(f"/prestamos/{prestamo.id}/inspeccion")
    assert res_insp.status_code == 200
    insp_data = res_insp.json()
    assert insp_data["checklist_inicial"]["completo"] is True
    assert "Pantalla sin arañazos" in insp_data["checklist_inicial"]["observaciones"]
    assert insp_data["garantia"]["tipo"] == "CARNET_UNIVERSITARIO"


@pytest.mark.e2e
def test_cancelar_prestamo_activo_por_gestor_exitoso():
    ahora = datetime.now(UTC)
    recurso_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=uuid4(),
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    prestamo_repository = FakePrestamoRepository([prestamo])
    recurso_repository = FakeRecursoRepository()
    recurso_repository.estado = EstadoRecurso.EN_USO
    service = PrestamoService(
        prestamo_repository=prestamo_repository,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
        recurso_repository=recurso_repository,
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    response = client.post(f"/prestamos/{prestamo.id}/cancelar")
    assert response.status_code == 200
    assert response.json() == {
        "detalle": "Préstamo cancelado exitosamente",
        "estado": "CANCELADO",
    }
    assert prestamo.estado == EstadoPrestamo.CANCELADO
    assert recurso_repository.estado == EstadoRecurso.DISPONIBLE


@pytest.mark.e2e
def test_cancelar_prestamo_inexistente_retorna_404():
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ADMINISTRADOR_SISTEMA]
    )

    response = client.post(f"/prestamos/{uuid4()}/cancelar")
    assert response.status_code == 404
    assert response.json()["detail"] == "Préstamo no encontrado"


@pytest.mark.e2e
def test_cancelar_prestamo_no_activo_retorna_409():
    ahora = datetime.now(UTC)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=5),
        estado=EstadoPrestamo.ENTREGADO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    response = client.post(f"/prestamos/{prestamo.id}/cancelar")
    assert response.status_code == 409
    assert "Solo se pueden cancelar préstamos pendientes" in response.json()["detail"]


@pytest.mark.e2e
def test_cancelar_prestamo_sin_rol_de_gestion_retorna_403():
    ahora = datetime.now(UTC)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=5),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ESTUDIANTE]
    )

    response = client.post(f"/prestamos/{prestamo.id}/cancelar")
    assert response.status_code == 403


@pytest.mark.e2e
def test_cancelar_prestamo_sin_token_retorna_401():
    response = client.post(f"/prestamos/{uuid4()}/cancelar")
    assert response.status_code == 401


@pytest.mark.e2e
def test_devolucion_con_danos_retiene_garantia_e2e():
    """RF-05: la devolución con daños físicos retiene la garantía asociada."""
    ahora = datetime.now(UTC)
    recurso_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=uuid4(),
        fecha_inicio=ahora - timedelta(days=2),
        fecha_fin=ahora + timedelta(days=2),
        estado=EstadoPrestamo.ENTREGADO,
    )
    fecha_reg = ahora - timedelta(days=2)
    garantia = Garantia(
        prestamo_id=prestamo.id,
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
    prestamo_repository = FakePrestamoRepository([prestamo])
    recurso_repository = FakeRecursoRepository()
    checklist_repository = FakeChecklistRepository()
    garantia_repository = FakeGarantiaRepository()
    garantia_repository.guardar(garantia)

    service = PrestamoService(
        prestamo_repository=prestamo_repository,
        checklist_repository=checklist_repository,
        garantia_repository=garantia_repository,
        recurso_repository=recurso_repository,
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    devolucion = client.post(
        f"/prestamos/{prestamo.id}/devolucion",
        json={
            "observaciones": "Pantalla rota",
            "danos_detectados": True,
            "fotos_urls": ["https://example.com/dano.png"],
        },
    )
    assert devolucion.status_code == 200

    insp = client.get(f"/prestamos/{prestamo.id}/inspeccion")
    assert insp.status_code == 200
    data = insp.json()
    assert data["garantia"]["estado"] == "RETENIDA"
    assert data["garantia"]["fecha_liberacion"] is None


@pytest.mark.e2e
def test_entrega_endpoints_sin_token_retornan_401():
    prestamo_id = uuid4()
    payload_iniciar = {
        "tipo_garantia": TipoGarantia.CARNET_UNIVERSITARIO.value,
        "compromiso_contenido": "Compromiso",
        "compromiso_firma_url": "https://example.com/firma.png",
        "compromiso_testigo": "Operador",
    }
    payload_completar = {
        **payload_iniciar,
        "observaciones_checklist": "Todo conforme",
        "fotos_urls": [],
    }

    assert client.post(f"/prestamos/{prestamo_id}/entrega/iniciar", json=payload_iniciar).status_code == 401
    assert client.post(
        f"/prestamos/{prestamo_id}/entrega/checklist/items",
        json={"observaciones": "Ok", "fotos_urls": []},
    ).status_code == 401
    assert client.post(f"/prestamos/{prestamo_id}/entrega/confirmar").status_code == 401
    assert client.post(f"/prestamos/{prestamo_id}/entrega/finalizar").status_code == 401
    assert client.post(f"/prestamos/{prestamo_id}/entrega/completar", json=payload_completar).status_code == 401


@pytest.mark.e2e
def test_entrega_endpoints_con_estudiante_retornan_403():
    prestamo_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ESTUDIANTE]
    )
    payload_iniciar = {
        "tipo_garantia": TipoGarantia.CARNET_UNIVERSITARIO.value,
        "compromiso_contenido": "Compromiso",
        "compromiso_firma_url": "https://example.com/firma.png",
        "compromiso_testigo": "Operador",
    }
    payload_completar = {
        **payload_iniciar,
        "observaciones_checklist": "Todo conforme",
        "fotos_urls": [],
    }

    assert client.post(f"/prestamos/{prestamo_id}/entrega/iniciar", json=payload_iniciar).status_code == 403
    assert client.post(
        f"/prestamos/{prestamo_id}/entrega/checklist/items",
        json={"observaciones": "Ok", "fotos_urls": []},
    ).status_code == 403
    assert client.post(f"/prestamos/{prestamo_id}/entrega/confirmar").status_code == 403
    assert client.post(f"/prestamos/{prestamo_id}/entrega/finalizar").status_code == 403
    assert client.post(f"/prestamos/{prestamo_id}/entrega/completar", json=payload_completar).status_code == 403


@pytest.mark.e2e
def test_inspeccion_seguridad_401_404_403_y_titular_200():
    titular_id = uuid4()
    otro_id = uuid4()
    ahora = datetime.now(UTC)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=titular_id,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=3),
        estado=EstadoPrestamo.ENTREGADO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    # Sin token -> 401
    assert client.get(f"/prestamos/{prestamo.id}/inspeccion").status_code == 401

    # Préstamo inexistente con usuario autenticado -> 404
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        otro_id, [RolUsuario.ESTUDIANTE]
    )
    assert client.get(f"/prestamos/{uuid4()}/inspeccion").status_code == 404

    # Otro estudiante -> 403
    assert client.get(f"/prestamos/{prestamo.id}/inspeccion").status_code == 403

    # Titular -> 200
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        titular_id, [RolUsuario.ESTUDIANTE]
    )
    assert client.get(f"/prestamos/{prestamo.id}/inspeccion").status_code == 200


@pytest.mark.e2e
def test_entrega_y_cancelacion_prestamo_expirado_retorna_409():
    """CL-9: iniciar/completar entrega o cancelar tras expirar la tolerancia de 30m retorna 409."""
    ahora = datetime.now(UTC)
    recurso_repo = FakeRecursoRepository()
    recurso_repo.obtener_por_id = lambda _id: SimpleNamespace(
        id=_id, estado=EstadoRecurso.EN_USO
    )
    prestamo_entrega = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=ahora - timedelta(minutes=31),
        fecha_fin=ahora + timedelta(hours=2),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    prestamo_cancelar = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=ahora - timedelta(minutes=31),
        fecha_fin=ahora + timedelta(hours=2),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo_entrega, prestamo_cancelar]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        recurso_repository=recurso_repo,
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    res_iniciar = client.post(
        f"/prestamos/{prestamo_entrega.id}/entrega/iniciar",
        json={
            "tipo_garantia": "CARNET_UNIVERSITARIO",
            "compromiso_contenido": "Compromiso",
            "compromiso_firma_url": "https://example.com/firma.png",
            "compromiso_testigo": "Operador",
        },
    )
    assert res_iniciar.status_code == 409
    assert prestamo_entrega.estado == EstadoPrestamo.CANCELADO
    assert recurso_repo.estado == EstadoRecurso.DISPONIBLE

    res_cancelar = client.post(f"/prestamos/{prestamo_cancelar.id}/cancelar")
    assert res_cancelar.status_code == 409
    assert prestamo_cancelar.estado == EstadoPrestamo.CANCELADO


@pytest.mark.e2e
def test_consulta_prestamos_marca_entregado_vencido_automaticamente():
    """RF-09 / CL-5: consultar /prestamos o historial pasa ENTREGADO vencido a VENCIDO."""
    ahora = datetime.now(UTC)
    titular_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=titular_id,
        fecha_inicio=ahora - timedelta(hours=3),
        fecha_fin=ahora - timedelta(minutes=1),
        estado=EstadoPrestamo.ENTREGADO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        titular_id, [RolUsuario.ESTUDIANTE]
    )

    res = client.get(f"/prestamos/usuarios/{titular_id}/historial")
    assert res.status_code == 200
    assert res.json()[0]["estado"] == "VENCIDO"
    assert prestamo.estado == EstadoPrestamo.VENCIDO


@pytest.mark.e2e
def test_historial_seguridad_401_403_y_gestion_200():
    titular_id = uuid4()
    otro_id = uuid4()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([]),
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    # Sin token -> 401
    assert client.get(f"/prestamos/usuarios/{titular_id}/historial").status_code == 401

    # Otro estudiante -> 403
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        otro_id, [RolUsuario.ESTUDIANTE]
    )
    assert client.get(f"/prestamos/usuarios/{titular_id}/historial").status_code == 403

    # Gestor -> 200
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )
    assert client.get(f"/prestamos/usuarios/{titular_id}/historial").status_code == 200


@pytest.mark.e2e
def test_respuestas_api_exponen_fechas_reales_tras_entrega_y_devolucion():
    titular_id = uuid4()
    ahora = datetime.now(UTC)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=titular_id,
        fecha_inicio=ahora - timedelta(minutes=10),
        fecha_fin=ahora + timedelta(days=3),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        recurso_repository=FakeRecursoRepository(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    res_entrega = client.post(
        f"/prestamos/{prestamo.id}/entrega/completar",
        json={
            "tipo_garantia": "CARNET_UNIVERSITARIO",
            "compromiso_contenido": "Compromiso",
            "compromiso_firma_url": "https://example.com/firma.png",
            "compromiso_testigo": "Operador",
            "observaciones_checklist": "Equipo completo",
            "fotos_urls": [],
        },
    )
    assert res_entrega.status_code == 200

    res_lista = client.get("/prestamos")
    assert res_lista.status_code == 200
    item_entregado = res_lista.json()[0]
    assert item_entregado["fecha_entrega_real"] is not None
    assert item_entregado["fecha_devolucion_real"] is None

    res_dev = client.post(f"/prestamos/{prestamo.id}/devolucion")
    assert res_dev.status_code == 200

    res_historial = client.get(f"/prestamos/usuarios/{titular_id}/historial")
    assert res_historial.status_code == 200
    item_devuelto = res_historial.json()[0]
    assert item_devuelto["fecha_entrega_real"] is not None
    assert item_devuelto["fecha_devolucion_real"] is not None


@pytest.mark.e2e
def test_obtener_checklist_plantilla_por_categoria_y_seguridad():
    ahora = datetime.now(UTC)
    recurso_id = uuid4()
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_id,
        usuario_id=uuid4(),
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=3),
        estado=EstadoPrestamo.POR_ENTREGAR,
    )
    recurso_repo = SimpleNamespace(
        obtener_por_id=lambda _id: SimpleNamespace(id=recurso_id, categoria="Libros"),
        actualizar_estado=lambda *_args: None,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        catalogo_service=recurso_repo,
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    # Sin token -> 401
    assert client.get(f"/prestamos/{prestamo.id}/checklist-plantilla").status_code == 401

    # Estudiante -> 403
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ESTUDIANTE]
    )
    assert client.get(f"/prestamos/{prestamo.id}/checklist-plantilla").status_code == 403

    # Gestor -> 200 con ítems de Libros
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )
    res = client.get(f"/prestamos/{prestamo.id}/checklist-plantilla")
    assert res.status_code == 200
    data = res.json()
    assert data["categoria"] == "Libros"
    assert any(item["id"] == "paginas" for item in data["items"])

    # Préstamo inexistente -> 404
    assert client.get(f"/prestamos/{uuid4()}/checklist-plantilla").status_code == 404


@pytest.mark.e2e
def test_devolucion_dano_parcial_y_dano_total_validacion_422_e2e():
    ahora = datetime.now(UTC)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=ahora - timedelta(days=1),
        fecha_fin=ahora + timedelta(days=2),
        estado=EstadoPrestamo.ENTREGADO,
    )
    recurso_repo = FakeRecursoRepository()
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        recurso_repository=recurso_repo,
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    # DANO_TOTAL sin monto -> 422
    res_invalido = client.post(
        f"/prestamos/{prestamo.id}/devolucion",
        json={"observaciones": "Pérdida total", "tipo_dano": "DANO_TOTAL"},
    )
    assert res_invalido.status_code == 422
    assert prestamo.estado == EstadoPrestamo.ENTREGADO

    # DANO_TOTAL con monto > 0 -> 200
    res_valido = client.post(
        f"/prestamos/{prestamo.id}/devolucion",
        json={
            "observaciones": "Pérdida total",
            "tipo_dano": "DANO_TOTAL",
            "monto_dano": 350.0,
        },
    )
    assert res_valido.status_code == 200
    assert res_valido.json()["tipo_dano"] == "DANO_TOTAL"
    assert recurso_repo.estado == EstadoRecurso.FUERA_DE_SERVICIO


@pytest.mark.e2e
def test_devolucion_mismo_dia_tarde_retorna_puntual_false_y_dias_retraso_cero():
    ahora = datetime.now(UTC)
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    # Garantizar que fecha_fin sea hoy pero anterior a ahora (si es 00:00:00, restamos 1 segundo)
    fin_hoy = ahora - timedelta(seconds=5)
    if fin_hoy.date() != ahora.date():
        fin_hoy = inicio_hoy + timedelta(seconds=1)
    prestamo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=inicio_hoy - timedelta(days=1),
        fecha_fin=fin_hoy,
        estado=EstadoPrestamo.ENTREGADO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([prestamo]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
        recurso_repository=FakeRecursoRepository(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )

    res = client.post(f"/prestamos/{prestamo.id}/devolucion")
    assert res.status_code == 200
    body = res.json()
    assert body["dias_retraso"] == 0
    assert body["puntual"] is False
    assert body["tipo_dano"] == "NINGUNO"





def test_consultar_historial_recurso_solo_gestion():
    recurso_objetivo = uuid4()
    p_objetivo = Prestamo(
        reserva_id=uuid4(),
        recurso_id=recurso_objetivo,
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 2, 10, 0, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )
    p_otro = Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 3, 10, 0, tzinfo=UTC),
        fecha_fin=datetime(2026, 10, 4, 10, 0, tzinfo=UTC),
        estado=EstadoPrestamo.DEVUELTO,
    )
    service = PrestamoService(
        prestamo_repository=FakePrestamoRepository([p_objetivo, p_otro]),
        checklist_repository=FakeChecklistRepository(),
        garantia_repository=FakeGarantiaRepository(),
    )
    app.dependency_overrides[get_prestamo_service] = lambda: service

    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ESTUDIANTE]
    )
    res_estudiante = client.get(f"/prestamos/recursos/{recurso_objetivo}/historial")
    assert res_estudiante.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.GESTOR_ALMACEN]
    )
    res_gestor = client.get(f"/prestamos/recursos/{recurso_objetivo}/historial")
    assert res_gestor.status_code == 200
    assert [item["id"] for item in res_gestor.json()] == [str(p_objetivo.id)]

    app.dependency_overrides[get_current_user] = lambda: _crear_usuario(
        uuid4(), [RolUsuario.ADMINISTRADOR_SISTEMA]
    )
    res_admin = client.get(f"/prestamos/recursos/{recurso_objetivo}/historial")
    assert res_admin.status_code == 200
    assert [item["id"] for item in res_admin.json()] == [str(p_objetivo.id)]
