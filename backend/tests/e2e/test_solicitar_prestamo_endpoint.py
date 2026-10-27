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
	def __init__(self, reserva):
		self.reserva = reserva
		self.solicitud_realizada = False

	def obtener_reserva(self, id_reserva):
		return self.reserva

	def convertir_a_prestamo(self, id_reserva):
		self.solicitud_realizada = True
		return True


@pytest.fixture(autouse=True)
def limpiar_overrides():
	yield
	app.dependency_overrides.clear()


def crear_usuario(usuario_id):
	return UsuarioDTO(
		id=usuario_id,
		nombre="Estudiante",
		correo="estudiante@example.test",
		telefono=None,
		roles=[RolUsuario.ESTUDIANTE],
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