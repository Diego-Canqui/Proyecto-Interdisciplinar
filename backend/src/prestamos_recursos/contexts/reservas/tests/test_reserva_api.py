from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from prestamos_recursos.contexts.reservas.application.reserva_service import ReservaService
from prestamos_recursos.contexts.reservas.infrastructure.repositories.memoria_reserva_repository import (
    MemoriaReservaRepository,
)
from prestamos_recursos.contexts.reservas.presentation.reserva_controller import obtener_servicio
from prestamos_recursos.main import app


@pytest.fixture
def cliente():
    servicio = ReservaService(MemoriaReservaRepository())
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(obtener_servicio, None)


def datos_reserva(horas=2, recurso_id=None):
    inicio = datetime.now(timezone.utc) + timedelta(hours=horas)
    return {
        "usuario_id": str(uuid4()),
        "recurso_id": recurso_id or str(uuid4()),
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": (inicio + timedelta(hours=1)).isoformat(),
    }


def test_crear_consultar_y_cancelar(cliente):
    datos = datos_reserva()
    respuesta = cliente.post("/reservas", json=datos)
    assert respuesta.status_code == 201
    reserva = respuesta.json()
    assert reserva["estado"] == "PENDIENTE"
    assert reserva["usuario_id"] == datos["usuario_id"]
    ruta = f"/reservas/{reserva['id']}"
    assert cliente.get(ruta).json() == reserva
    cancelada = cliente.patch(f"{ruta}/cancelar")
    assert cancelada.status_code == 200
    assert cancelada.json()["estado"] == "CANCELADA"
    assert cliente.get(ruta).json()["estado"] == "CANCELADA"
    assert cliente.patch(f"{ruta}/cancelar").status_code == 409


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
    conflicto = cliente.post("/reservas", json=cruzada)
    assert conflicto.status_code == 409
    assert conflicto.json()["detail"] == (
        "el recurso ya tiene una reserva activa en ese horario"
    )

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
    recurso = str(uuid4())
    ids = []
    for horas in (6, 3, -3, 1):
        respuesta = cliente.post("/reservas", json=datos_reserva(horas, recurso))
        assert respuesta.status_code == 201
        ids.append(respuesta.json()["id"])
    assert cliente.patch(f"/reservas/{ids[3]}/cancelar").status_code == 200
    assert cliente.post("/reservas", json=datos_reserva()).status_code == 201
    cola = cliente.get(f"/reservas/recurso/{recurso}/cola")
    assert cola.status_code == 200
    assert [reserva["id"] for reserva in cola.json()] == [ids[1], ids[0]]
    assert cliente.get(f"/reservas/recurso/{uuid4()}/cola").json() == []
