from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import UsuarioDTO
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
	get_current_user,
)
from prestamos_recursos.contexts.reservas.application.dto.reserva_dto import ReservaDTO
from prestamos_recursos.contexts.reservas.presentation.reserva_controller import obtener_servicio
from prestamos_recursos.main import app

client = TestClient(app)


class FakeReservaService:
	def __init__(self, reserva=None):
		self.reserva = reserva
		self.solicitud_realizada = False

	def obtener_reserva(self, id_reserva):
		return self.reserva

	def obtener_todas(self):
		return [self.reserva] if self.reserva else []

	def confirmar_reserva(self, id_reserva):
		return self.reserva

	def cancelar_reserva(self, id_reserva):
		return True

	def convertir_a_prestamo(self, id_reserva):
		self.solicitud_realizada = True
		return True


@pytest.fixture(autouse=True)
def limpiar_overrides():
	yield
	app.dependency_overrides.clear()


def crear_usuario(usuario_id, rol=RolUsuario.ESTUDIANTE):
	return UsuarioDTO(
		id=usuario_id,
		nombre=f"Usuario-{rol.value}",
		correo=f"{rol.value.lower()}@example.test",
		telefono=None,
		roles=[rol],
		estado=True,
	)


def crear_reserva(reserva_id, usuario_id):
	return ReservaDTO(
		id=reserva_id,
		usuario_id=usuario_id,
		recurso_id=uuid4(),
		fecha_inicio=datetime(2026, 10, 22, tzinfo=UTC),
		fecha_fin=datetime(2026, 10, 23, tzinfo=UTC),
		estado="CONFIRMADA",
	)


@pytest.mark.e2e
def test_solicitar_prestamo_desde_reserva_del_usuario():
	usuario_id = uuid4()
	reserva_id = uuid4()
	service = FakeReservaService(crear_reserva(reserva_id, usuario_id))
	app.dependency_overrides[obtener_servicio] = lambda: service
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(usuario_id)

	response = client.post(f"/reservas/{reserva_id}/prestamo")

	assert response.status_code == 201
	assert response.json() == {"detalle": "Préstamo creado desde la reserva"}
	assert service.solicitud_realizada is True


@pytest.mark.e2e
def test_solicitar_prestamo_rechaza_reserva_de_otro_usuario():
	service = FakeReservaService(crear_reserva(uuid4(), uuid4()))
	app.dependency_overrides[obtener_servicio] = lambda: service
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(uuid4())

	response = client.post(f"/reservas/{service.reserva.id}/prestamo")

	assert response.status_code == 403
	assert service.solicitud_realizada is False


@pytest.mark.e2e
def test_listar_todas_reservas_gestor_y_admin():
	usuario_gestor = crear_usuario(uuid4(), RolUsuario.GESTOR_ALMACEN)
	usuario_admin = crear_usuario(uuid4(), RolUsuario.ADMINISTRADOR_SISTEMA)
	service = FakeReservaService(crear_reserva(uuid4(), uuid4()))
	app.dependency_overrides[obtener_servicio] = lambda: service

	app.dependency_overrides[get_current_user] = lambda: usuario_gestor
	res_gestor = client.get("/reservas")
	assert res_gestor.status_code == 200
	assert len(res_gestor.json()) == 1

	app.dependency_overrides[get_current_user] = lambda: usuario_admin
	res_admin = client.get("/reservas")
	assert res_admin.status_code == 200
	assert len(res_admin.json()) == 1


@pytest.mark.e2e
def test_listar_todas_reservas_rechaza_estudiante():
	usuario_estudiante = crear_usuario(uuid4(), RolUsuario.ESTUDIANTE)
	service = FakeReservaService(crear_reserva(uuid4(), uuid4()))
	app.dependency_overrides[obtener_servicio] = lambda: service
	app.dependency_overrides[get_current_user] = lambda: usuario_estudiante

	response = client.get("/reservas")
	assert response.status_code == 403


@pytest.mark.e2e
def test_confirmar_reserva_permite_titular_y_gestor_rechaza_ajeno():
	titular_id = uuid4()
	reserva_id = uuid4()
	otro_id = uuid4()
	gestor_id = uuid4()

	reserva = crear_reserva(reserva_id, titular_id)
	service = FakeReservaService(reserva)
	app.dependency_overrides[obtener_servicio] = lambda: service

	# Titular: 200
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(titular_id, RolUsuario.ESTUDIANTE)
	res_titular = client.patch(f"/reservas/{reserva_id}/confirmar")
	assert res_titular.status_code == 200

	# Gestor: 200
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(gestor_id, RolUsuario.GESTOR_ALMACEN)
	res_gestor = client.patch(f"/reservas/{reserva_id}/confirmar")
	assert res_gestor.status_code == 200

	# Otro estudiante: 403
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(otro_id, RolUsuario.ESTUDIANTE)
	res_otro = client.patch(f"/reservas/{reserva_id}/confirmar")
	assert res_otro.status_code == 403


@pytest.mark.e2e
def test_cancelar_reserva_permite_titular_y_gestor_rechaza_ajeno():
	titular_id = uuid4()
	reserva_id = uuid4()
	otro_id = uuid4()
	gestor_id = uuid4()

	reserva = crear_reserva(reserva_id, titular_id)
	service = FakeReservaService(reserva)
	app.dependency_overrides[obtener_servicio] = lambda: service

	# Titular: 200
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(titular_id, RolUsuario.ESTUDIANTE)
	res_titular = client.patch(f"/reservas/{reserva_id}/cancelar")
	assert res_titular.status_code == 200

	# Gestor: 200
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(gestor_id, RolUsuario.GESTOR_ALMACEN)
	res_gestor = client.patch(f"/reservas/{reserva_id}/cancelar")
	assert res_gestor.status_code == 200

	# Otro estudiante: 403
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(otro_id, RolUsuario.ESTUDIANTE)
	res_otro = client.patch(f"/reservas/{reserva_id}/cancelar")
	assert res_otro.status_code == 403


@pytest.mark.e2e
def test_solicitar_prestamo_permite_gestor_almacen_en_reserva_ajena():
	titular_id = uuid4()
	reserva_id = uuid4()
	gestor_id = uuid4()

	service = FakeReservaService(crear_reserva(reserva_id, titular_id))
	app.dependency_overrides[obtener_servicio] = lambda: service
	app.dependency_overrides[get_current_user] = lambda: crear_usuario(gestor_id, RolUsuario.GESTOR_ALMACEN)

	response = client.post(f"/reservas/{reserva_id}/prestamo")
	assert response.status_code == 201
	assert response.json() == {"detalle": "Préstamo creado desde la reserva"}
	assert service.solicitud_realizada is True
