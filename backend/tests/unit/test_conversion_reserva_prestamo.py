from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.reservas.application.dto.reserva_dto import (
    CrearReservaDTO,
    ReservaDTO,
)
from prestamos_recursos.contexts.reservas.application.reserva_service import ReservaService
from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.contexts.reservas.domain.services.algoritmo_prioridad_service import (
    AlgoritmoPrioridadService,
)


class FakeReservaRepository:
    def __init__(self, reserva=None, reservas=None):
        self.reserva = reserva
        self.reservas = list(reservas) if reservas is not None else ([reserva] if reserva else [])
        self.saved = []

    def obtener_por_id(self, id_reserva):
        for r in self.reservas:
            if r.id == id_reserva:
                return r
        if self.reserva and self.reserva.id == id_reserva:
            return self.reserva
        return None

    def obtener_todas(self):
        return list(self.reservas)

    def obtener_activas_por_recurso(self, id_recurso):
        return [
            r
            for r in self.reservas
            if r.recurso_id == id_recurso
            and r.estado in {EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA}
        ]

    def obtener_cola_por_recurso(self, id_recurso):
        return [
            r
            for r in self.reservas
            if r.recurso_id == id_recurso and r.estado == EstadoReserva.PENDIENTE
        ]

    def guardar(self, reserva):
        self.saved.append(reserva)
        for idx, r in enumerate(self.reservas):
            if r.id == reserva.id:
                self.reservas[idx] = reserva
                return
        self.reservas.append(reserva)


class FakePrestamoRepository:
    def __init__(self):
        self.saved = []

    def guardar(self, prestamo):
        self.saved.append(prestamo)


class FakeRecursoRepository:
    def __init__(self, estado=EstadoRecurso.DISPONIBLE, existe=True):
        self.recurso = SimpleNamespace(estado=estado) if existe else None

    def obtener_por_id(self, id_recurso):
        return self.recurso

    def actualizar_estado(self, id_recurso, estado):
        self.recurso.estado = estado


class FakeReputacionService:
    def __init__(self, puntajes: dict[UUID, int] | None = None):
        self.puntajes = puntajes or {}

    def obtener_perfil(self, usuario_id: UUID):
        puntaje = self.puntajes.get(usuario_id, 500)
        return SimpleNamespace(puntaje=puntaje)


def make_reserva(estado=EstadoReserva.CONFIRMADA):
    return Reserva(
        usuario_id=uuid4(),
        recurso_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 6, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 10, 7, tzinfo=timezone.utc),
        estado=estado,
    )


def make_prestamo_service(prestamo_repository, recurso_repository=None):
    return PrestamoService(
        prestamo_repository=prestamo_repository,
        checklist_repository=SimpleNamespace(),
        garantia_repository=SimpleNamespace(),
        recurso_repository=recurso_repository or FakeRecursoRepository(),
    )


def test_convertir_reserva_confirmada_crea_prestamo_activo():
    reserva = make_reserva()
    reserva_repository = FakeReservaRepository(reserva)
    prestamo_repository = FakePrestamoRepository()
    recurso_repository = FakeRecursoRepository()
    service = ReservaService(
        reserva_repository,
        make_prestamo_service(prestamo_repository, recurso_repository),
    )

    assert service.convertir_a_prestamo(reserva.id) is True

    prestamo = prestamo_repository.saved[0]
    assert prestamo.reserva_id == reserva.id
    assert prestamo.usuario_id == reserva.usuario_id
    assert prestamo.recurso_id == reserva.recurso_id
    assert prestamo.fecha_inicio == reserva.fecha_inicio
    assert prestamo.fecha_fin == reserva.fecha_fin
    assert prestamo.estado == EstadoPrestamo.ACTIVO
    assert reserva.estado == EstadoReserva.CONVERTIDA
    assert reserva_repository.saved == [reserva]
    assert recurso_repository.recurso.estado == EstadoRecurso.EN_USO


def test_convertir_reserva_no_confirmada_no_crea_prestamo():
    reserva = make_reserva(EstadoReserva.PENDIENTE)
    reserva_repository = FakeReservaRepository(reserva)
    prestamo_repository = FakePrestamoRepository()
    service = ReservaService(
        reserva_repository,
        make_prestamo_service(prestamo_repository),
    )

    assert service.convertir_a_prestamo(reserva.id) is False
    assert prestamo_repository.saved == []
    assert reserva_repository.saved == []


def test_convertir_reserva_rechaza_recurso_no_disponible():
    reserva = make_reserva()
    reserva_repository = FakeReservaRepository(reserva)
    prestamo_repository = FakePrestamoRepository()
    recurso_repository = FakeRecursoRepository(EstadoRecurso.EN_USO)
    service = ReservaService(
        reserva_repository,
        make_prestamo_service(prestamo_repository, recurso_repository),
    )

    try:
        service.convertir_a_prestamo(reserva.id)
    except ValueError as error:
        assert str(error) == "Recurso no disponible"
    else:
        raise AssertionError("Se esperaba rechazar un recurso no disponible")

    assert prestamo_repository.saved == []
    assert reserva.estado == EstadoReserva.CONFIRMADA


def test_convertir_reserva_rechaza_recurso_inexistente():
    reserva = make_reserva()
    reserva_repository = FakeReservaRepository(reserva)
    prestamo_repository = FakePrestamoRepository()
    recurso_repository = FakeRecursoRepository(existe=False)
    service = ReservaService(
        reserva_repository,
        make_prestamo_service(prestamo_repository, recurso_repository),
    )

    try:
        service.convertir_a_prestamo(reserva.id)
    except ValueError as error:
        assert str(error) == "Recurso no encontrado"
    else:
        raise AssertionError("Se esperaba rechazar un recurso inexistente")

    assert prestamo_repository.saved == []
    assert reserva.estado == EstadoReserva.CONFIRMADA


def test_obtener_todas_devuelve_reservas_de_distintos_usuarios():
    u1 = uuid4()
    u2 = uuid4()
    r1 = Reserva(
        usuario_id=u1,
        recurso_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 6, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 10, 7, tzinfo=timezone.utc),
        estado=EstadoReserva.CONFIRMADA,
    )
    r2 = Reserva(
        usuario_id=u2,
        recurso_id=uuid4(),
        fecha_inicio=datetime(2026, 10, 8, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 10, 9, tzinfo=timezone.utc),
        estado=EstadoReserva.PENDIENTE,
    )
    repo = FakeReservaRepository(reservas=[r1, r2])
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))

    resultado = service.obtener_todas()

    assert len(resultado) == 2
    assert all(isinstance(dto, ReservaDTO) for dto in resultado)
    assert {dto.id for dto in resultado} == {r1.id, r2.id}
    assert {dto.usuario_id for dto in resultado} == {u1, u2}


# --- Tests AlgoritmoPrioridadService ---


def test_prioridad_orden_por_reputacion_descendente():
    servicio = AlgoritmoPrioridadService()
    u_800 = uuid4()
    u_500 = uuid4()
    u_300 = uuid4()
    recurso_id = uuid4()

    r1 = Reserva.crear(
        usuario_id=u_300,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc),
    )
    r2 = Reserva.crear(
        usuario_id=u_800,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc),
    )
    r3 = Reserva.crear(
        usuario_id=u_500,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc),
    )

    puntajes = {u_800: 800, u_500: 500, u_300: 300}
    ordenadas = servicio.ordenar_cola_espera([r1, r2, r3], puntajes)

    assert ordenadas == [r2, r3, r1]


def test_prioridad_desempate_por_fecha_inicio():
    servicio = AlgoritmoPrioridadService()
    u1 = uuid4()
    u2 = uuid4()
    recurso_id = uuid4()

    r_temprano = Reserva.crear(
        usuario_id=u1,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
    )
    r_tarde = Reserva.crear(
        usuario_id=u2,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc),
    )

    # Ambos con el mismo puntaje de reputación
    puntajes = {u1: 600, u2: 600}
    ordenadas = servicio.ordenar_cola_espera([r_tarde, r_temprano], puntajes)
    assert ordenadas == [r_temprano, r_tarde]


def test_prioridad_estabilidad_mismo_puntaje_y_fecha():
    servicio = AlgoritmoPrioridadService()
    u1 = uuid4()
    u2 = uuid4()
    recurso_id = uuid4()

    r1 = Reserva.crear(
        usuario_id=u1,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
    )
    r2 = Reserva.crear(
        usuario_id=u2,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
    )

    # Mismo puntaje y misma fecha
    puntajes = {u1: 500, u2: 500}
    assert servicio.ordenar_cola_espera([r1, r2], puntajes) == [r1, r2]
    assert servicio.ordenar_cola_espera([r2, r1], puntajes) == [r2, r1]


def test_prioridad_puntaje_por_defecto():
    servicio = AlgoritmoPrioridadService()
    u_con_puntaje = uuid4()
    u_sin_puntaje = uuid4()
    recurso_id = uuid4()

    r_con = Reserva.crear(
        usuario_id=u_con_puntaje,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
    )
    r_sin = Reserva.crear(
        usuario_id=u_sin_puntaje,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
    )

    # u_sin_puntaje no está en el diccionario -> asume 500
    # u_con_puntaje tiene 400 -> 500 > 400, por lo que r_sin debe ir primero
    puntajes = {u_con_puntaje: 400}
    ordenadas = servicio.ordenar_cola_espera([r_con, r_sin], puntajes)
    assert ordenadas == [r_sin, r_con]


# --- Tests ReservaService ---


def _horario_futuro(horas_inicio: float = 24, duracion_horas: float = 2):
    inicio = datetime.now(timezone.utc) + timedelta(hours=horas_inicio)
    return inicio, inicio + timedelta(hours=duracion_horas)


def test_crear_reserva_horario_libre_confirma_automaticamente():
    repo = FakeReservaRepository()
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))
    inicio, fin = _horario_futuro()
    datos = CrearReservaDTO(
        usuario_id=uuid4(),
        recurso_id=uuid4(),
        fecha_inicio=inicio,
        fecha_fin=fin,
    )

    reserva_dto = service.crear_reserva(datos)
    assert reserva_dto.estado == "CONFIRMADA"
    assert len(repo.saved) == 1
    assert repo.saved[0].estado == EstadoReserva.CONFIRMADA


def test_crear_reserva_horario_ocupado_otro_usuario_guarda_pendiente():
    u1 = uuid4()
    u2 = uuid4()
    recurso_id = uuid4()
    inicio, fin = _horario_futuro()
    confirmada_existente = Reserva.crear(
        usuario_id=u1,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    confirmada_existente.confirmar()
    repo = FakeReservaRepository(reservas=[confirmada_existente])
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))

    datos = CrearReservaDTO(
        usuario_id=u2,
        recurso_id=recurso_id,
        fecha_inicio=inicio + timedelta(minutes=30),
        fecha_fin=inicio + timedelta(minutes=90),
    )

    reserva_dto = service.crear_reserva(datos)
    assert reserva_dto.estado == "PENDIENTE"
    # Guardada en pendiente sin lanzar excepción
    guardada = repo.obtener_por_id(reserva_dto.id)
    assert guardada is not None
    assert guardada.estado == EstadoReserva.PENDIENTE


def test_crear_reserva_mismo_usuario_duplica_lanza_error():
    u1 = uuid4()
    recurso_id = uuid4()
    inicio, fin = _horario_futuro()
    confirmada_existente = Reserva.crear(
        usuario_id=u1,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    confirmada_existente.confirmar()
    repo = FakeReservaRepository(reservas=[confirmada_existente])
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))

    datos = CrearReservaDTO(
        usuario_id=u1,
        recurso_id=recurso_id,
        fecha_inicio=inicio + timedelta(hours=1),
        fecha_fin=fin + timedelta(hours=1),
    )

    with pytest.raises(ValueError, match="ya tienes una reserva activa para este recurso en ese horario"):
        service.crear_reserva(datos)


def test_confirmar_reserva_ignora_pendientes_y_valida_solo_confirmadas():
    recurso_id = uuid4()
    inicio, fin = _horario_futuro()
    r_pendiente = Reserva.crear(
        usuario_id=uuid4(),
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    otra_pendiente = Reserva.crear(
        usuario_id=uuid4(),
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    repo = FakeReservaRepository(reservas=[r_pendiente, otra_pendiente])
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))

    # Se puede confirmar r_pendiente aunque otra_pendiente coincida en horario porque está PENDIENTE
    dto = service.confirmar_reserva(r_pendiente.id)
    assert dto.estado == "CONFIRMADA"


def test_confirmar_reserva_choca_con_otra_confirmada_lanza_error():
    recurso_id = uuid4()
    inicio, fin = _horario_futuro()
    r_confirmada = Reserva.crear(
        usuario_id=uuid4(),
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    r_confirmada.confirmar()
    r_pendiente = Reserva.crear(
        usuario_id=uuid4(),
        recurso_id=recurso_id,
        fecha_inicio=inicio + timedelta(hours=1),
        fecha_fin=fin + timedelta(hours=1),
    )
    repo = FakeReservaRepository(reservas=[r_confirmada, r_pendiente])
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))

    with pytest.raises(ValueError, match="el recurso ya tiene una reserva confirmada en ese horario"):
        service.confirmar_reserva(r_pendiente.id)


def test_cancelar_reserva_confirmada_promueve_candidata_con_mayor_reputacion():
    recurso_id = uuid4()
    u_confirmado = uuid4()
    u_bajo = uuid4()
    u_alto = uuid4()
    inicio, fin = _horario_futuro()

    r_confirmada = Reserva.crear(
        usuario_id=u_confirmado,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    r_confirmada.confirmar()

    r_bajo = Reserva.crear(
        usuario_id=u_bajo,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    r_alto = Reserva.crear(
        usuario_id=u_alto,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )

    repo = FakeReservaRepository(reservas=[r_confirmada, r_bajo, r_alto])
    reputacion = FakeReputacionService(puntajes={u_bajo: 300, u_alto: 750})
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()), reputacion)

    assert service.cancelar_reserva(r_confirmada.id) is True
    assert r_confirmada.estado == EstadoReserva.CANCELADA
    assert r_alto.estado == EstadoReserva.CONFIRMADA
    assert r_bajo.estado == EstadoReserva.PENDIENTE


def test_cancelar_reserva_pendiente_no_promueve_ninguna():
    recurso_id = uuid4()
    inicio, fin = _horario_futuro()
    r1 = Reserva.crear(
        usuario_id=uuid4(),
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    r2 = Reserva.crear(
        usuario_id=uuid4(),
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    repo = FakeReservaRepository(reservas=[r1, r2])
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))

    assert service.cancelar_reserva(r1.id) is True
    assert r1.estado == EstadoReserva.CANCELADA
    assert r2.estado == EstadoReserva.PENDIENTE


def test_obtener_cola_espera_ordena_por_reputacion():
    recurso_id = uuid4()
    u1 = uuid4()
    u2 = uuid4()
    inicio, fin = _horario_futuro()

    r1 = Reserva.crear(
        usuario_id=u1,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    r2 = Reserva.crear(
        usuario_id=u2,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )

    repo = FakeReservaRepository(reservas=[r1, r2])
    reputacion = FakeReputacionService(puntajes={u1: 400, u2: 900})
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()), reputacion)

    cola = service.obtener_cola_espera(recurso_id)
    assert len(cola) == 2
    assert cola[0].id == r2.id
    assert cola[1].id == r1.id

