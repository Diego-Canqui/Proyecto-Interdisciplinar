from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.catalogo.infrastructure.models.recurso_model import RecursoModel
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import (
    PerfilReputacionModel,
    SancionModel,
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
    with SessionLocal() as session:
        session.execute(delete(ReservaModel))
        # Asegurar ID_USUARIO_PRUEBA registrado con nivel EXCELENTE (límite 5)
        usuario = session.get(UsuarioModel, ID_USUARIO_PRUEBA)
        if usuario is None:
            otro = session.query(UsuarioModel).filter(UsuarioModel.correo == "reservas@test.com").first()
            if otro is not None:
                session.delete(otro)
                session.flush()
            usuario = UsuarioModel(
                id=ID_USUARIO_PRUEBA,
                nombre="Usuario de prueba",
                correo="reservas@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            )
            session.add(usuario)
            session.flush()

        perfil = (
            session.query(PerfilReputacionModel)
            .filter(PerfilReputacionModel.usuario_id == ID_USUARIO_PRUEBA)
            .first()
        )
        if perfil is None:
            perfil = PerfilReputacionModel(
                id=uuid4(),
                usuario_id=ID_USUARIO_PRUEBA,
                puntos=850,
                nivel=NivelReputacion.EXCELENTE,
                fecha_actualizacion=datetime.now(UTC),
            )
            session.add(perfil)
        else:
            perfil.puntos = 850
            perfil.nivel = NivelReputacion.EXCELENTE
        session.commit()
    with TestClient(app) as client:
        try:
            yield client
        finally:
            app.dependency_overrides.pop(get_current_user, None)


def datos_reserva(horas=2, recurso_id=None):
    candidato = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    while candidato.weekday() >= 5:
        candidato += timedelta(days=1)
    inicio = candidato
    return {
        "usuario_id": str(ID_USUARIO_PRUEBA),
        "recurso_id": recurso_id or str(uuid4()),
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": (inicio + timedelta(hours=horas)).isoformat(),
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
            UsuarioModel(
                id=u_alto_id,
                nombre="Alto",
                correo=f"alto_{uuid4()}@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            )
        )
        session.flush()
        session.add(
            PerfilReputacionModel(
                id=uuid4(),
                usuario_id=u_bajo_id,
                puntos=300,
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
            UsuarioModel(
                id=u_alto_id,
                nombre="Alto2",
                correo=f"alto2_{uuid4()}@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            ),
        ])
        session.flush()
        session.add_all([
            PerfilReputacionModel(
                id=uuid4(),
                usuario_id=u_bajo_id,
                puntos=350,
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


def test_rechazo_403_gestor_o_admin_solicitar_reserva(cliente):
    # Gestor de almacén no puede solicitar reservas
    app.dependency_overrides[get_current_user] = lambda: USUARIO_GESTOR
    resp_gestor = cliente.post("/reservas", json=datos_reserva() | {"usuario_id": str(ID_GESTOR_PRUEBA)})
    assert resp_gestor.status_code == 403
    assert resp_gestor.json()["detail"] == (
        "las cuentas de gestión y administración no pueden solicitar reservas para sí mismas"
    )

    # Administrador del sistema tampoco puede
    id_admin = uuid4()
    usuario_admin = UsuarioDTO(
        id=id_admin,
        nombre="Admin",
        correo="admin@test.com",
        telefono=None,
        roles=[RolUsuario.ADMINISTRADOR_SISTEMA],
        estado=True,
    )
    app.dependency_overrides[get_current_user] = lambda: usuario_admin
    resp_admin = cliente.post("/reservas", json=datos_reserva() | {"usuario_id": str(id_admin)})
    assert resp_admin.status_code == 403
    assert resp_admin.json()["detail"] == (
        "las cuentas de gestión y administración no pueden solicitar reservas para sí mismas"
    )


def test_rechazo_duracion_mayor_a_7_dias_y_exito_exacto_7_dias(cliente):
    candidato = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    while candidato.weekday() >= 5:
        candidato += timedelta(days=1)
    inicio = candidato
    # 8 días: supera límite 7 días -> 409
    datos_8_dias = {
        "usuario_id": str(ID_USUARIO_PRUEBA),
        "recurso_id": str(uuid4()),
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": (inicio + timedelta(days=8)).isoformat(),
    }
    resp = cliente.post("/reservas", json=datos_8_dias)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "la duración máxima de una reserva es de 7 días"

    # Exactamente 7 días -> 201
    datos_7_dias = {
        "usuario_id": str(ID_USUARIO_PRUEBA),
        "recurso_id": str(uuid4()),
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": (inicio + timedelta(days=7)).isoformat(),
    }
    resp_ok = cliente.post("/reservas", json=datos_7_dias)
    assert resp_ok.status_code == 201


def test_rechazo_por_sancion_vigente_en_solicitud_confirmacion_y_prestamo(cliente):
    u_sancionado_id = uuid4()
    p_id = uuid4()
    ahora = datetime.now(UTC)

    with SessionLocal() as session:
        session.add(
            UsuarioModel(
                id=u_sancionado_id,
                nombre="Sancionado",
                correo=f"sanc_{uuid4()}@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            )
        )
        session.flush()
        perfil = PerfilReputacionModel(
            id=p_id,
            usuario_id=u_sancionado_id,
            puntos=400,
            nivel=NivelReputacion.NORMAL,
        )
        session.add(perfil)
        session.flush()
        sancion = SancionModel(
            id=uuid4(),
            perfil_reputacion_id=p_id,
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-100,
            monto_descuento=0,
            motivo="Daño en equipo",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=10),
            activa=True,
        )
        session.add(sancion)
        session.commit()

    u_sancionado_dto = UsuarioDTO(
        id=u_sancionado_id,
        nombre="Sancionado",
        correo="sancionado@test.com",
        telefono=None,
        roles=[RolUsuario.ESTUDIANTE],
        estado=True,
    )

    # 1. Solicitar reserva con usuario sancionado -> 409
    app.dependency_overrides[get_current_user] = lambda: u_sancionado_dto
    candidato = (ahora + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    while candidato.weekday() >= 5:
        candidato += timedelta(days=1)
    datos = {
        "usuario_id": str(u_sancionado_id),
        "recurso_id": str(uuid4()),
        "fecha_inicio": candidato.isoformat(),
        "fecha_fin": (candidato + timedelta(hours=2)).isoformat(),
    }
    resp_crear = cliente.post("/reservas", json=datos)
    assert resp_crear.status_code == 409
    assert "sanción vigente" in resp_crear.json()["detail"]

    # 2. Confirmar reserva de usuario sancionado -> 409
    reserva_pendiente_id = uuid4()
    with SessionLocal() as session:
        session.add(
            ReservaModel(
                id=reserva_pendiente_id,
                usuario_id=u_sancionado_id,
                recurso_id=uuid4(),
                fecha_inicio=candidato + timedelta(days=1),
                fecha_fin=candidato + timedelta(days=1, hours=2),
                estado=EstadoReserva.PENDIENTE,
            )
        )
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: USUARIO_GESTOR
    resp_conf = cliente.patch(f"/reservas/{reserva_pendiente_id}/confirmar")
    assert resp_conf.status_code == 409
    assert "sanción vigente" in resp_conf.json()["detail"]

    # 3. Convertir a préstamo reserva confirmada de usuario sancionado -> 409
    reserva_confirmada_id = uuid4()
    with SessionLocal() as session:
        session.add(
            ReservaModel(
                id=reserva_confirmada_id,
                usuario_id=u_sancionado_id,
                recurso_id=uuid4(),
                fecha_inicio=ahora + timedelta(minutes=30),
                fecha_fin=ahora + timedelta(hours=2),
                estado=EstadoReserva.CONFIRMADA,
            )
        )
        session.commit()

    resp_prestamo = cliente.post(f"/reservas/{reserva_confirmada_id}/prestamo")
    assert resp_prestamo.status_code == 409
    assert "sanción vigente" in resp_prestamo.json()["detail"]


def test_rechazo_limite_operaciones_simultaneas_segun_nivel(cliente):
    # Usuario con nivel BAJO (límite 1)
    u_bajo_id = uuid4()
    with SessionLocal() as session:
        session.add(
            UsuarioModel(
                id=u_bajo_id,
                nombre="Usuario Bajo",
                correo=f"bajo_{uuid4()}@test.com",
                password_hash="hash",
                estado=True,
                roles=["ESTUDIANTE"],
            )
        )
        session.flush()
        session.add(
            PerfilReputacionModel(
                id=uuid4(),
                usuario_id=u_bajo_id,
                puntos=200,
                nivel=NivelReputacion.BAJO,
            )
        )
        session.commit()

    u_bajo_dto = UsuarioDTO(
        id=u_bajo_id,
        nombre="Usuario Bajo",
        correo="bajo@test.com",
        telefono=None,
        roles=[RolUsuario.ESTUDIANTE],
        estado=True,
    )
    app.dependency_overrides[get_current_user] = lambda: u_bajo_dto

    ahora = datetime.now(UTC)
    candidato = (ahora + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    while candidato.weekday() >= 5:
        candidato += timedelta(days=1)
    # Primera reserva -> 201
    datos1 = {
        "usuario_id": str(u_bajo_id),
        "recurso_id": str(uuid4()),
        "fecha_inicio": candidato.isoformat(),
        "fecha_fin": (candidato + timedelta(hours=2)).isoformat(),
    }
    resp1 = cliente.post("/reservas", json=datos1)
    assert resp1.status_code == 201

    # Segunda reserva activa -> 409 (límite 1 alcanzado)
    datos2 = {
        "usuario_id": str(u_bajo_id),
        "recurso_id": str(uuid4()),
        "fecha_inicio": (candidato + timedelta(hours=3)).isoformat(),
        "fecha_fin": (candidato + timedelta(hours=5)).isoformat(),
    }
    resp2 = cliente.post("/reservas", json=datos2)
    assert resp2.status_code == 409
    assert "límite de 1 operaciones activas simultáneas" in resp2.json()["detail"]


def test_convertir_a_prestamo_fuera_de_ventana_retorna_409(cliente):
    """RF-04: intentar convertir a préstamo fuera de ventana (inicio - 1h <= ahora <= fin) retorna 409."""
    reserva_id = uuid4()
    ahora = datetime.now(UTC)
    with SessionLocal() as session:
        session.add(
            ReservaModel(
                id=reserva_id,
                usuario_id=ID_USUARIO_PRUEBA,
                recurso_id=uuid4(),
                fecha_inicio=ahora + timedelta(days=3),
                fecha_fin=ahora + timedelta(days=3, hours=2),
                estado=EstadoReserva.CONFIRMADA,
            )
        )
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: USUARIO_GESTOR
    resp = cliente.post(f"/reservas/{reserva_id}/prestamo")
    assert resp.status_code == 409
    assert "el préstamo solo puede iniciarse desde 1 hora antes del horario reservado" in resp.json()["detail"]


def test_solicitar_reserva_recurso_en_mantenimiento_o_fuera_de_servicio_retorna_409(cliente):
    """RF-03: un recurso en mantenimiento o fuera de servicio no admite reservas (409)."""
    rec_mant_id = uuid4()
    rec_fuera_id = uuid4()

    with SessionLocal() as session:
        session.add(
            RecursoModel(
                id=rec_mant_id,
                nombre="Cámara Mant",
                descripcion="En taller",
                categoria="Fotografía",
                estado=EstadoRecurso.MANTENIMIENTO,
                marca="Sony",
                modelo="Alpha",
                numero_serie=f"SN-{rec_mant_id}",
                color="Negro",
                estado_fisico="Regular",
                foto_url="https://example.com/cam.png",
            )
        )
        session.add(
            RecursoModel(
                id=rec_fuera_id,
                nombre="Lente Roto",
                descripcion="Averiado",
                categoria="Fotografía",
                estado=EstadoRecurso.FUERA_DE_SERVICIO,
                marca="Canon",
                modelo="50mm",
                numero_serie=f"SN-{rec_fuera_id}",
                color="Negro",
                estado_fisico="Malo",
                foto_url="https://example.com/lente.png",
            )
        )
        session.commit()

    # Mantenimiento -> 409
    datos_mant = datos_reserva(recurso_id=str(rec_mant_id))
    resp_mant = cliente.post("/reservas", json=datos_mant)
    assert resp_mant.status_code == 409
    assert (
        resp_mant.json()["detail"]
        == "el recurso no admite reservas por encontrarse en mantenimiento o fuera de servicio"
    )

    # Fuera de servicio -> 409
    datos_fuera = datos_reserva(recurso_id=str(rec_fuera_id))
    resp_fuera = cliente.post("/reservas", json=datos_fuera)
    assert resp_fuera.status_code == 409
    assert (
        resp_fuera.json()["detail"]
        == "el recurso no admite reservas por encontrarse en mantenimiento o fuera de servicio"
    )


