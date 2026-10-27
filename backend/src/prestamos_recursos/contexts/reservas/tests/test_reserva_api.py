from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import (
    PerfilReputacionModel,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.usuario_model import (
    UsuarioModel,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    get_current_user,
)
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.contexts.reservas.infrastructure.models.reserva_model import (
    ReservaModel,
)
from prestamos_recursos.main import app
from prestamos_recursos.shared.database import Base, SessionLocal, engine

ID_USUARIO_PRUEBA = uuid4()
USUARIO_PRUEBA = UsuarioDTO(
    id=ID_USUARIO_PRUEBA,
    nombre="Usuario de prueba",
    correo="reservas@test.com",
    telefono=None,
    roles=[RolUsuario.ESTUDIANTE],
    estado=True,
)

ID_GESTOR_PRUEBA = uuid4()
USUARIO_GESTOR = UsuarioDTO(
    id=ID_GESTOR_PRUEBA,
    nombre="Gestor de prueba",
    correo="gestor@test.com",
    telefono=None,
    roles=[RolUsuario.GESTOR_ALMACEN],
    estado=True,
)


@pytest.fixture
def cliente():
    app.dependency_overrides[get_current_user] = lambda: USUARIO_PRUEBA
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        with SessionLocal() as session:
            session.execute(delete(ReservaModel))
            session.commit()
        try:
            yield client
        finally:
            app.dependency_overrides.pop(get_current_user, None)


def datos_reserva(horas=2, recurso_id=None):
    inicio = datetime.now(UTC) + timedelta(hours=horas)
    return {
        "usuario_id": str(ID_USUARIO_PRUEBA),
        "recurso_id": recurso_id or str(uuid4()),
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": (inicio + timedelta(hours=1)).isoformat(),
    }


def test_crear_consultar_y_cancelar(cliente):
    datos = datos_reserva()
    respuesta = cliente.post("/reservas", json=datos)
    assert respuesta.status_code == 201
    reserva = respuesta.json()
    assert reserva["estado"] == "CONFIRMADA"
    assert reserva["usuario_id"] == datos["usuario_id"]
    ruta = f"/reservas/{reserva['id']}"
    assert cliente.get(ruta).json() == reserva
    cancelada = cliente.patch(f"{ruta}/cancelar")
    assert cancelada.status_code == 200
    assert cancelada.json()["estado"] == "CANCELADA"
    assert cliente.get(ruta).json()["estado"] == "CANCELADA"
    assert cliente.patch(f"{ruta}/cancelar").status_code == 409


def test_confirmar_y_listar_por_usuario(cliente):
    id_reserva = uuid4()
    inicio = datetime.now(UTC) + timedelta(hours=2)
    fin = inicio + timedelta(hours=3)
    with SessionLocal() as session:
        session.add(
            ReservaModel(
                id=id_reserva,
                usuario_id=ID_USUARIO_PRUEBA,
                recurso_id=uuid4(),
                fecha_inicio=inicio,
                fecha_fin=fin,
                estado=EstadoReserva.PENDIENTE,
            )
        )
        session.commit()

    # Titular sin rol de gestión recibe 403
    rechazo_titular = cliente.patch(f"/reservas/{id_reserva}/confirmar")
    assert rechazo_titular.status_code == 403
    assert rechazo_titular.json()["detail"] == "solo el personal de gestión puede confirmar reservas"

    # Gestor de almacén puede confirmar
    app.dependency_overrides[get_current_user] = lambda: USUARIO_GESTOR
    confirmada = cliente.patch(f"/reservas/{id_reserva}/confirmar")
    assert confirmada.status_code == 200
    assert confirmada.json()["estado"] == "CONFIRMADA"
    assert cliente.patch(f"/reservas/{id_reserva}/confirmar").status_code == 409

    # Listar por usuario
    app.dependency_overrides[get_current_user] = lambda: USUARIO_PRUEBA
    listado = cliente.get(f"/reservas/usuario/{ID_USUARIO_PRUEBA}")
    assert listado.status_code == 200
    assert [reserva["id"] for reserva in listado.json()] == [str(id_reserva)]


def test_usuario_no_puede_reservar_a_nombre_de_otro(cliente):
    datos = datos_reserva() | {"usuario_id": str(uuid4())}
    assert cliente.post("/reservas", json=datos).status_code == 403


def test_usuario_no_puede_listar_reservas_de_otro(cliente):
    respuesta = cliente.get(f"/reservas/usuario/{uuid4()}")
    assert respuesta.status_code == 403


def test_rechaza_cruce_y_permite_horarios_libres(cliente):
    recurso = str(uuid4())
    primera = datos_reserva(recurso_id=recurso)
    creada = cliente.post("/reservas", json=primera)
    assert creada.status_code == 201

    inicio = datetime.fromisoformat(primera["fecha_inicio"])
    fin = datetime.fromisoformat(primera["fecha_fin"])
    cruzada = primera | {
        "fecha_inicio": (inicio + timedelta(minutes=30)).isoformat(),
        "fecha_fin": (fin + timedelta(minutes=30)).isoformat(),
    }
    # Mismo usuario intentando cruzar horario -> 409
    conflicto = cliente.post("/reservas", json=cruzada)
    assert conflicto.status_code == 409
    assert conflicto.json()["detail"] == (
        "ya tienes una reserva activa para este recurso en ese horario"
    )

    # Otro usuario pidiendo horario ocupado por la confirmada -> 201 PENDIENTE
    otro_id = uuid4()
    otro_usuario = UsuarioDTO(
        id=otro_id,
        nombre="Otro usuario",
        correo="otro@test.com",
        telefono=None,
        roles=[RolUsuario.ESTUDIANTE],
        estado=True,
    )
    app.dependency_overrides[get_current_user] = lambda: otro_usuario
    cruzada_otro = cruzada | {"usuario_id": str(otro_id)}
    pendiente = cliente.post("/reservas", json=cruzada_otro)
    assert pendiente.status_code == 201
    assert pendiente.json()["estado"] == "PENDIENTE"

    # Restaurar usuario de prueba
    app.dependency_overrides[get_current_user] = lambda: USUARIO_PRUEBA

    consecutiva = primera | {
        "fecha_inicio": fin.isoformat(),
        "fecha_fin": (fin + timedelta(hours=1)).isoformat(),
    }
    assert cliente.post("/reservas", json=consecutiva).status_code == 201

    para_otro_recurso = cruzada | {"recurso_id": str(uuid4())}
    assert cliente.post("/reservas", json=para_otro_recurso).status_code == 201

    id_primera = creada.json()["id"]
    assert cliente.patch(f"/reservas/{id_primera}/cancelar").status_code == 200
    assert cliente.post("/reservas", json=primera).status_code == 201


@pytest.mark.parametrize("caso", ["fechas_iguales", "fechas_invertidas", "zona", "uuid", "faltante"])
def test_datos_invalidos(cliente, caso):
    datos = datos_reserva()
    if caso == "fechas_iguales":
        datos["fecha_fin"] = datos["fecha_inicio"]
    elif caso == "fechas_invertidas":
        datos["fecha_inicio"], datos["fecha_fin"] = datos["fecha_fin"], datos["fecha_inicio"]
    elif caso == "zona":
        datos["fecha_fin"] = datetime.fromisoformat(datos["fecha_fin"]).replace(tzinfo=None).isoformat()
    elif caso == "uuid":
        datos["usuario_id"] = "invalido"
    else:
        del datos["recurso_id"]
    assert cliente.post("/reservas", json=datos).status_code == 422


def test_reserva_inexistente(cliente):
    ruta = f"/reservas/{uuid4()}"
    assert cliente.get(ruta).status_code == 404
    assert cliente.patch(f"{ruta}/cancelar").status_code == 404
    assert cliente.get("/reservas/no-es-uuid").status_code == 422


def test_cola_ordenada_y_filtrada(cliente):
    recurso = uuid4()
    ids = []
    with SessionLocal() as session:
        for horas in (6, 3, -3, 1):
            r_id = uuid4()
            inicio = datetime.now(UTC) + timedelta(hours=horas)
            session.add(
                ReservaModel(
                    id=r_id,
                    usuario_id=ID_USUARIO_PRUEBA,
                    recurso_id=recurso,
                    fecha_inicio=inicio,
                    fecha_fin=inicio + timedelta(hours=1),
                    estado=EstadoReserva.PENDIENTE,
                )
            )
            ids.append(str(r_id))
        session.commit()

    assert cliente.patch(f"/reservas/{ids[3]}/cancelar").status_code == 200
    assert cliente.post("/reservas", json=datos_reserva()).status_code == 201
    cola = cliente.get(f"/reservas/recurso/{recurso}/cola")
    assert cola.status_code == 200
    assert [reserva["id"] for reserva in cola.json()] == [ids[1], ids[0]]
    assert cliente.get(f"/reservas/recurso/{uuid4()}/cola").json() == []


def test_errores_de_estado_y_acceso(cliente):
    # Titular sin rol de gestión recibe 403 al intentar confirmar cualquier reserva
    assert cliente.patch(f"/reservas/{uuid4()}/confirmar").status_code == 403

    # Con usuario gestor:
    app.dependency_overrides[get_current_user] = lambda: USUARIO_GESTOR

    # 404 para reserva inexistente
    assert cliente.patch(f"/reservas/{uuid4()}/confirmar").status_code == 404

    # 409 para reserva vencida
    id_vencida = uuid4()
    with SessionLocal() as session:
        session.add(
            ReservaModel(
                id=id_vencida,
                usuario_id=ID_USUARIO_PRUEBA,
                recurso_id=uuid4(),
                fecha_inicio=datetime.now(UTC) - timedelta(hours=3),
                fecha_fin=datetime.now(UTC) - timedelta(hours=2),
                estado=EstadoReserva.PENDIENTE,
            )
        )
        session.commit()
    assert cliente.patch(f"/reservas/{id_vencida}/confirmar").status_code == 409

    # 409 para reserva cancelada
    id_cancelada = uuid4()
    with SessionLocal() as session:
        session.add(
            ReservaModel(
                id=id_cancelada,
                usuario_id=ID_USUARIO_PRUEBA,
                recurso_id=uuid4(),
                fecha_inicio=datetime.now(UTC) + timedelta(hours=1),
                fecha_fin=datetime.now(UTC) + timedelta(hours=2),
                estado=EstadoReserva.CANCELADA,
            )
        )
        session.commit()
    assert cliente.patch(f"/reservas/{id_cancelada}/confirmar").status_code == 409


def test_cola_ordenada_por_reputacion(cliente):
    recurso = uuid4()
    u_bajo_id = uuid4()
    u_alto_id = uuid4()

    with SessionLocal() as session:
        session.add(
            UsuarioModel(
                id=u_bajo_id,
                nombre="Bajo",
                correo=f"bajo_{uuid4()}@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            )
        )
        session.add(
            PerfilReputacionModel(
                id=uuid4(),
                usuario_id=u_bajo_id,
                puntos=300,
            )
        )
        session.add(
            UsuarioModel(
                id=u_alto_id,
                nombre="Alto",
                correo=f"alto_{uuid4()}@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            )
        )
        session.add(
            PerfilReputacionModel(
                id=uuid4(),
                usuario_id=u_alto_id,
                puntos=850,
            )
        )
        inicio = datetime.now(UTC) + timedelta(hours=2)
        fin = inicio + timedelta(hours=2)
        r_bajo = ReservaModel(
            id=uuid4(),
            usuario_id=u_bajo_id,
            recurso_id=recurso,
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado=EstadoReserva.PENDIENTE,
        )
        r_alto = ReservaModel(
            id=uuid4(),
            usuario_id=u_alto_id,
            recurso_id=recurso,
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado=EstadoReserva.PENDIENTE,
        )
        session.add_all([r_bajo, r_alto])
        session.commit()
        id_bajo = str(r_bajo.id)
        id_alto = str(r_alto.id)

    cola = cliente.get(f"/reservas/recurso/{recurso}/cola")
    assert cola.status_code == 200
    ids_en_cola = [r["id"] for r in cola.json()]
    assert ids_en_cola == [id_alto, id_bajo]


def test_cancelar_confirmada_promueve_reserva_pendiente_mas_prioritaria(cliente):
    recurso = uuid4()
    u_titular_id = ID_USUARIO_PRUEBA
    u_bajo_id = uuid4()
    u_alto_id = uuid4()

    inicio = datetime.now(UTC) + timedelta(hours=3)
    fin = inicio + timedelta(hours=2)
    id_confirmada = uuid4()
    id_bajo = uuid4()
    id_alto = uuid4()

    with SessionLocal() as session:
        session.add_all([
            UsuarioModel(
                id=u_bajo_id,
                nombre="Bajo2",
                correo=f"bajo2_{uuid4()}@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            ),
            PerfilReputacionModel(
                id=uuid4(),
                usuario_id=u_bajo_id,
                puntos=350,
            ),
            UsuarioModel(
                id=u_alto_id,
                nombre="Alto2",
                correo=f"alto2_{uuid4()}@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            ),
            PerfilReputacionModel(
                id=uuid4(),
                usuario_id=u_alto_id,
                puntos=900,
            ),
            ReservaModel(
                id=id_confirmada,
                usuario_id=u_titular_id,
                recurso_id=recurso,
                fecha_inicio=inicio,
                fecha_fin=fin,
                estado=EstadoReserva.CONFIRMADA,
            ),
            ReservaModel(
                id=id_bajo,
                usuario_id=u_bajo_id,
                recurso_id=recurso,
                fecha_inicio=inicio,
                fecha_fin=fin,
                estado=EstadoReserva.PENDIENTE,
            ),
            ReservaModel(
                id=id_alto,
                usuario_id=u_alto_id,
                recurso_id=recurso,
                fecha_inicio=inicio,
                fecha_fin=fin,
                estado=EstadoReserva.PENDIENTE,
            ),
        ])
        session.commit()

    # Titular cancela su reserva confirmada
    cancelar_resp = cliente.patch(f"/reservas/{id_confirmada}/cancelar")
    assert cancelar_resp.status_code == 200
    assert cancelar_resp.json()["estado"] == "CANCELADA"

    with SessionLocal() as session:
        reserva_alto = session.get(ReservaModel, id_alto)
        reserva_bajo = session.get(ReservaModel, id_bajo)
        assert reserva_alto.estado == EstadoReserva.CONFIRMADA
        assert reserva_bajo.estado == EstadoReserva.PENDIENTE

