from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
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

    def obtener_por_usuario(self, id_usuario):
        return [r for r in self.reservas if r.usuario_id == id_usuario]

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

    def obtener_por_usuario(self, id_usuario):
        return [p for p in self.saved if getattr(p, "usuario_id", None) == id_usuario]


class FakeRecursoRepository:
    def __init__(self, estado=EstadoRecurso.DISPONIBLE, existe=True):
        self.recurso = SimpleNamespace(estado=estado) if existe else None

    def obtener_por_id(self, id_recurso):
        return self.recurso

    def actualizar_estado(self, id_recurso, estado):
        self.recurso.estado = estado


class FakeReputacionService:
    def __init__(
        self,
        puntajes: dict[UUID, int] | None = None,
        elegibles: dict[UUID, bool] | None = None,
        niveles: dict[UUID, NivelReputacion] | None = None,
    ):
        self.puntajes = puntajes or {}
        self.elegibles = elegibles or {}
        self.niveles = niveles or {}

    def obtener_perfil(self, usuario_id: UUID):
        puntaje = self.puntajes.get(usuario_id, 500)
        nivel = self.niveles.get(usuario_id, NivelReputacion.NORMAL)
        return SimpleNamespace(puntaje=puntaje, nivel=nivel)

    def consultar_elegibilidad_lectura(self, usuario_id: UUID):
        es_elegible = self.elegibles.get(usuario_id, True)
        if not es_elegible:
            return SimpleNamespace(
                elegible=False, razon="tienes una sanción vigente de tipo DANO_PARCIAL"
            )
        return SimpleNamespace(elegible=True, razon=None)

    def consultar_nivel_lectura(self, usuario_id: UUID) -> NivelReputacion:
        return self.niveles.get(usuario_id, NivelReputacion.NORMAL)

    def consultar_puntaje_lectura(self, usuario_id: UUID) -> int:
        return self.puntajes.get(usuario_id, 500)


def make_reserva(estado=EstadoReserva.CONFIRMADA):
    inicio = datetime.now(timezone.utc) + timedelta(minutes=30)
    return Reserva(
        usuario_id=uuid4(),
        recurso_id=uuid4(),
        fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(hours=2),
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
        fecha_inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
    )
    r2 = Reserva.crear(
        usuario_id=u_800,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
    )
    r3 = Reserva.crear(
        usuario_id=u_500,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
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
        fecha_inicio=datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
    )
    r_tarde = Reserva.crear(
        usuario_id=u2,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc),
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
        fecha_inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
    )
    r2 = Reserva.crear(
        usuario_id=u2,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
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
        fecha_inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
    )
    r_sin = Reserva.crear(
        usuario_id=u_sin_puntaje,
        recurso_id=recurso_id,
        fecha_inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
    )

    # u_sin_puntaje no está en el diccionario -> asume 500
    # u_con_puntaje tiene 400 -> 500 > 400, por lo que r_sin debe ir primero
    puntajes = {u_con_puntaje: 400}
    ordenadas = servicio.ordenar_cola_espera([r_con, r_sin], puntajes)
    assert ordenadas == [r_sin, r_con]


# --- Tests ReservaService ---


def _horario_futuro(horas_inicio: float = 24, duracion_horas: float = 2):
    ahora = datetime.now(timezone.utc)
    candidato = (ahora + timedelta(hours=horas_inicio)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    while candidato.weekday() >= 5:
        candidato += timedelta(days=1)
    return candidato, candidato + timedelta(hours=duracion_horas)


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


# --- Tests RF-05: Duración máxima de reserva (7 días) ---


def test_reserva_crear_limite_7_dias():
    u_id = uuid4()
    r_id = uuid4()
    inicio = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)

    # Exactamente 7 días (168 horas) permitido
    fin_7_dias = inicio + timedelta(days=7)
    reserva = Reserva.crear(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=inicio,
        fecha_fin=fin_7_dias,
    )
    assert reserva.fecha_fin == fin_7_dias

    # Más de 7 días (7 días + 1 segundo) lanza ValueError
    with pytest.raises(ValueError, match="la duración máxima de una reserva es de 7 días"):
        Reserva.crear(
            usuario_id=u_id,
            recurso_id=r_id,
            fecha_inicio=inicio,
            fecha_fin=inicio + timedelta(days=7, seconds=1),
        )


def test_reserva_constructor_directo_permite_mas_de_7_dias_para_bd():
    u_id = uuid4()
    r_id = uuid4()
    inicio = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
    fin_10_dias = inicio + timedelta(days=10)

    # Constructor directo (usado por ORM / mapeadores) no lanza ValueError por 7 días
    reserva = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=inicio,
        fecha_fin=fin_10_dias,
    )
    assert reserva.fecha_fin == fin_10_dias


def test_reserva_crear_rechaza_fin_de_semana():
    u_id = uuid4()
    r_id = uuid4()
    sabado = datetime(2026, 11, 7, 10, 0, tzinfo=timezone.utc)
    domingo = datetime(2026, 11, 8, 10, 0, tzinfo=timezone.utc)

    # Inicio en sábado
    with pytest.raises(
        ValueError,
        match="el horario de atención para entregas y devoluciones es de lunes a viernes de 08:00 a 20:00",
    ):
        Reserva.crear(
            usuario_id=u_id,
            recurso_id=r_id,
            fecha_inicio=sabado,
            fecha_fin=sabado + timedelta(hours=2),
        )

    # Fin en domingo
    with pytest.raises(
        ValueError,
        match="el horario de atención para entregas y devoluciones es de lunes a viernes de 08:00 a 20:00",
    ):
        Reserva.crear(
            usuario_id=u_id,
            recurso_id=r_id,
            fecha_inicio=datetime(2026, 11, 6, 10, 0, tzinfo=timezone.utc),
            fecha_fin=domingo,
        )


def test_reserva_crear_rechaza_fuera_de_horario_atencion():
    u_id = uuid4()
    r_id = uuid4()
    lunes = datetime(2026, 11, 2, tzinfo=timezone.utc)

    # 07:59 (antes de las 08:00)
    with pytest.raises(
        ValueError,
        match="el horario de atención para entregas y devoluciones es de lunes a viernes de 08:00 a 20:00",
    ):
        Reserva.crear(
            usuario_id=u_id,
            recurso_id=r_id,
            fecha_inicio=lunes.replace(hour=7, minute=59),
            fecha_fin=lunes.replace(hour=10, minute=0),
        )

    # 20:01 (después de las 20:00)
    with pytest.raises(
        ValueError,
        match="el horario de atención para entregas y devoluciones es de lunes a viernes de 08:00 a 20:00",
    ):
        Reserva.crear(
            usuario_id=u_id,
            recurso_id=r_id,
            fecha_inicio=lunes.replace(hour=18, minute=0),
            fecha_fin=lunes.replace(hour=20, minute=1),
        )

    # 08:00:00 y 20:00:00 bordes exactos permitidos
    r_borde = Reserva.crear(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=lunes.replace(hour=8, minute=0, second=0),
        fecha_fin=lunes.replace(hour=20, minute=0, second=0),
    )
    assert r_borde.fecha_inicio.hour == 8
    assert r_borde.fecha_fin.hour == 20

    # Reserva multidía de viernes 15:00 a lunes 15:00 es aceptada
    viernes = datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc)
    lunes_sgte = datetime(2026, 11, 9, 15, 0, tzinfo=timezone.utc)
    r_multidia = Reserva.crear(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=viernes,
        fecha_fin=lunes_sgte,
    )
    assert r_multidia.fecha_inicio == viernes
    assert r_multidia.fecha_fin == lunes_sgte


def test_reserva_crear_rechaza_duracion_menor_a_1_hora():
    u_id = uuid4()
    r_id = uuid4()
    inicio = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)

    # 30 minutos
    with pytest.raises(ValueError, match="la duración mínima de una reserva es de 1 hora"):
        Reserva.crear(
            usuario_id=u_id,
            recurso_id=r_id,
            fecha_inicio=inicio,
            fecha_fin=inicio + timedelta(minutes=30),
        )

    # 59 minutos
    with pytest.raises(ValueError, match="la duración mínima de una reserva es de 1 hora"):
        Reserva.crear(
            usuario_id=u_id,
            recurso_id=r_id,
            fecha_inicio=inicio,
            fecha_fin=inicio + timedelta(minutes=59),
        )

    # Exactamente 60 minutos permitido
    r_60m = Reserva.crear(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(hours=1),
    )
    assert r_60m.fecha_fin - r_60m.fecha_inicio == timedelta(hours=1)


# --- Tests RF-03: Bloqueo por sanción vigente ---


def test_crear_reserva_usuario_con_sancion_vigente_lanza_error():
    u_sancionado = uuid4()
    inicio, fin = _horario_futuro()
    datos = CrearReservaDTO(
        usuario_id=u_sancionado,
        recurso_id=uuid4(),
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    repo = FakeReservaRepository()
    reputacion = FakeReputacionService(elegibles={u_sancionado: False})
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()), reputacion)

    with pytest.raises(ValueError, match="sanción vigente"):
        service.crear_reserva(datos)


def test_confirmar_reserva_usuario_con_sancion_vigente_lanza_error():
    u_sancionado = uuid4()
    inicio, fin = _horario_futuro()
    reserva = Reserva.crear(
        usuario_id=u_sancionado,
        recurso_id=uuid4(),
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    repo = FakeReservaRepository(reserva=reserva)
    reputacion = FakeReputacionService(elegibles={u_sancionado: False})
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()), reputacion)

    with pytest.raises(ValueError, match="sanción vigente"):
        service.confirmar_reserva(reserva.id)


def test_convertir_a_prestamo_usuario_con_sancion_vigente_lanza_error():
    u_sancionado = uuid4()
    inicio, fin = _horario_futuro()
    reserva = Reserva.crear(
        usuario_id=u_sancionado,
        recurso_id=uuid4(),
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    reserva.confirmar()
    repo = FakeReservaRepository(reserva=reserva)
    reputacion = FakeReputacionService(elegibles={u_sancionado: False})
    service = ReservaService(
        repo,
        make_prestamo_service(FakePrestamoRepository(), FakeRecursoRepository()),
        reputacion,
    )

    with pytest.raises(ValueError, match="sanción vigente"):
        service.convertir_a_prestamo(reserva.id)


def test_cancelar_reserva_omite_candidato_sancionado_en_promocion():
    recurso_id = uuid4()
    u_confirmado = uuid4()
    u_sancionado = uuid4()
    u_limpio = uuid4()
    inicio, fin = _horario_futuro()

    r_confirmada = Reserva.crear(
        usuario_id=u_confirmado,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    r_confirmada.confirmar()

    r_sancionado = Reserva.crear(
        usuario_id=u_sancionado,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    r_limpio = Reserva.crear(
        usuario_id=u_limpio,
        recurso_id=recurso_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
    )

    repo = FakeReservaRepository(reservas=[r_confirmada, r_sancionado, r_limpio])
    # u_sancionado tiene mayor puntaje (900 vs 500) pero está sancionado (elegible=False)
    reputacion = FakeReputacionService(
        puntajes={u_sancionado: 900, u_limpio: 500},
        elegibles={u_sancionado: False, u_limpio: True},
    )
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()), reputacion)

    assert service.cancelar_reserva(r_confirmada.id) is True
    # u_sancionado fue saltado; se promovió a u_limpio
    assert r_sancionado.estado == EstadoReserva.PENDIENTE
    assert r_limpio.estado == EstadoReserva.CONFIRMADA


# --- Tests RF-04: Límite de operaciones activas simultáneas según NivelReputacion ---


class FakePrestamoServiceConContador:
    def __init__(self, prestamos_en_curso: dict[UUID, int] | None = None):
        self.prestamos_en_curso = prestamos_en_curso or {}

    def contar_prestamos_en_curso(self, id_usuario: UUID) -> int:
        return self.prestamos_en_curso.get(id_usuario, 0)


@pytest.mark.parametrize(
    ("nivel", "limite"),
    [
        (NivelReputacion.BAJO, 1),
        (NivelReputacion.NORMAL, 2),
        (NivelReputacion.BUENO, 3),
        (NivelReputacion.EXCELENTE, 5),
    ],
)
def test_limite_operaciones_simultaneas_por_nivel(nivel, limite):
    u_id = uuid4()
    reputacion = FakeReputacionService(niveles={u_id: nivel})
    repo = FakeReservaRepository()
    prestamos_service = FakePrestamoServiceConContador()
    service = ReservaService(repo, prestamos_service, reputacion)

    inicio, fin = _horario_futuro(horas_inicio=10)

    # Puede crear hasta `limite` reservas
    fechas_habiles = []
    candidato = inicio
    while len(fechas_habiles) < limite + 1:
        if candidato.weekday() < 5:
            fechas_habiles.append(candidato)
        candidato += timedelta(days=1)

    for i in range(limite):
        f_inicio = fechas_habiles[i]
        f_fin = f_inicio + (fin - inicio)
        datos = CrearReservaDTO(
            usuario_id=u_id,
            recurso_id=uuid4(),
            fecha_inicio=f_inicio,
            fecha_fin=f_fin,
        )
        service.crear_reserva(datos)

    # La siguiente reserva que supere el límite debe ser rechazada con ValueError
    f_extra_inicio = fechas_habiles[limite]
    f_extra_fin = f_extra_inicio + (fin - inicio)
    datos_extra = CrearReservaDTO(
        usuario_id=u_id,
        recurso_id=uuid4(),
        fecha_inicio=f_extra_inicio,
        fecha_fin=f_extra_fin,
    )
    with pytest.raises(ValueError, match=f"has alcanzado el límite de {limite} operaciones activas"):
        service.crear_reserva(datos_extra)


def test_limite_operaciones_suma_reservas_activas_y_prestamos_en_curso():
    u_id = uuid4()
    # NORMAL tiene límite 2
    reputacion = FakeReputacionService(niveles={u_id: NivelReputacion.NORMAL})
    repo = FakeReservaRepository()
    # Ya tiene 1 préstamo en curso
    prestamos_service = FakePrestamoServiceConContador(prestamos_en_curso={u_id: 1})
    service = ReservaService(repo, prestamos_service, reputacion)

    inicio, fin = _horario_futuro(horas_inicio=10)

    # 1 reserva permitida (1 préstamo + 1 reserva = 2)
    datos1 = CrearReservaDTO(
        usuario_id=u_id,
        recurso_id=uuid4(),
        fecha_inicio=inicio,
        fecha_fin=fin,
    )
    service.crear_reserva(datos1)

    # 2da reserva supera el límite de 2 operaciones activas simultáneas
    siguiente_dia = inicio + timedelta(days=1)
    while siguiente_dia.weekday() >= 5:
        siguiente_dia += timedelta(days=1)

    datos2 = CrearReservaDTO(
        usuario_id=u_id,
        recurso_id=uuid4(),
        fecha_inicio=siguiente_dia,
        fecha_fin=siguiente_dia + (fin - inicio),
    )
    with pytest.raises(ValueError, match="has alcanzado el límite de 2 operaciones activas"):
        service.crear_reserva(datos2)


def test_crear_reserva_rechaza_fecha_en_el_pasado_y_permite_tolerancia_5_min():
    repo = FakeReservaRepository()
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))
    u_id = uuid4()
    r_id = uuid4()
    ahora_fijo = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)

    # 11:50 es > 5 minutos en el pasado -> ValueError
    datos_pasado = CrearReservaDTO(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=ahora_fijo - timedelta(minutes=10),
        fecha_fin=ahora_fijo + timedelta(hours=1),
    )
    with pytest.raises(ValueError, match="no se pueden crear reservas en el pasado"):
        service.crear_reserva(datos_pasado, ahora=ahora_fijo)

    # 11:58 está dentro de la tolerancia de 5 minutos -> permitido
    datos_tolerancia = CrearReservaDTO(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=ahora_fijo - timedelta(minutes=2),
        fecha_fin=ahora_fijo + timedelta(hours=1),
    )
    reserva = service.crear_reserva(datos_tolerancia, ahora=ahora_fijo)
    assert reserva.id is not None


def test_crear_reserva_rechaza_anticipacion_mayor_a_30_dias():
    repo = FakeReservaRepository()
    service = ReservaService(repo, make_prestamo_service(FakePrestamoRepository()))
    u_id = uuid4()
    r_id = uuid4()
    ahora_fijo = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)

    # 31 días después (miércoles 2 de diciembre de 2026 a las 12:00) -> > 30 días
    inicio_lejano = ahora_fijo + timedelta(days=31)
    datos = CrearReservaDTO(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=inicio_lejano,
        fecha_fin=inicio_lejano + timedelta(hours=2),
    )
    with pytest.raises(
        ValueError, match="solo se puede reservar con un máximo de 30 días de anticipación"
    ):
        service.crear_reserva(datos, ahora=ahora_fijo)


def test_crear_reserva_rechaza_recurso_mantenimiento_o_fuera_de_servicio_y_permite_en_uso():
    u_id = uuid4()
    r_id_mantenimiento = uuid4()
    r_id_fuera = uuid4()
    r_id_en_uso = uuid4()
    r_id_disponible = uuid4()

    recursos_catalogo = {
        r_id_mantenimiento: SimpleNamespace(estado=EstadoRecurso.MANTENIMIENTO),
        r_id_fuera: SimpleNamespace(estado=EstadoRecurso.FUERA_DE_SERVICIO),
        r_id_en_uso: SimpleNamespace(estado=EstadoRecurso.EN_USO),
        r_id_disponible: SimpleNamespace(estado=EstadoRecurso.DISPONIBLE),
    }

    class FakeCatalogoService:
        def obtener_por_id(self, id_r):
            return recursos_catalogo.get(id_r)

    repo = FakeReservaRepository()
    service = ReservaService(
        repo,
        make_prestamo_service(FakePrestamoRepository()),
        catalogo_service=FakeCatalogoService(),
    )
    ahora_fijo = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
    inicio = ahora_fijo + timedelta(days=1)
    fin = inicio + timedelta(hours=2)

    # Mantenimiento -> rechazo
    with pytest.raises(
        ValueError,
        match="el recurso no admite reservas por encontrarse en mantenimiento o fuera de servicio",
    ):
        service.crear_reserva(
            CrearReservaDTO(
                usuario_id=u_id,
                recurso_id=r_id_mantenimiento,
                fecha_inicio=inicio,
                fecha_fin=fin,
            ),
            ahora=ahora_fijo,
        )

    # Fuera de servicio -> rechazo
    with pytest.raises(
        ValueError,
        match="el recurso no admite reservas por encontrarse en mantenimiento o fuera de servicio",
    ):
        service.crear_reserva(
            CrearReservaDTO(
                usuario_id=u_id,
                recurso_id=r_id_fuera,
                fecha_inicio=inicio,
                fecha_fin=fin,
            ),
            ahora=ahora_fijo,
        )

    # EN_USO -> permitido (puede reservarse o entrar a cola)
    reserva_en_uso = service.crear_reserva(
        CrearReservaDTO(
            usuario_id=u_id,
            recurso_id=r_id_en_uso,
            fecha_inicio=inicio,
            fecha_fin=fin,
        ),
        ahora=ahora_fijo,
    )
    assert reserva_en_uso.id is not None

    # DISPONIBLE -> permitido
    reserva_disp = service.crear_reserva(
        CrearReservaDTO(
            usuario_id=u_id,
            recurso_id=r_id_disponible,
            fecha_inicio=inicio,
            fecha_fin=fin,
        ),
        ahora=ahora_fijo,
    )
    assert reserva_disp.id is not None


def test_convertir_a_prestamo_valida_ventana_temporal():
    u_id = uuid4()
    r_id = uuid4()
    inicio = datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)
    fin = datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc)

    reserva = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
        estado=EstadoReserva.CONFIRMADA,
    )
    repo = FakeReservaRepository(reserva)
    prestamo_repo = FakePrestamoRepository()
    recurso_repo = FakeRecursoRepository()
    service = ReservaService(repo, make_prestamo_service(prestamo_repo, recurso_repo))

    # Demasiado temprano: 1h y 1 minuto antes (12:59) -> ValueError
    with pytest.raises(
        ValueError,
        match="el préstamo solo puede iniciarse desde 1 hora antes del horario reservado y hasta antes de su vencimiento",
    ):
        service.convertir_a_prestamo(reserva.id, ahora=inicio - timedelta(hours=1, minutes=1))

    # Demasiado tarde: después de fecha_fin (16:01) -> ValueError
    with pytest.raises(
        ValueError,
        match="el préstamo solo puede iniciarse desde 1 hora antes del horario reservado y hasta antes de su vencimiento",
    ):
        service.convertir_a_prestamo(reserva.id, ahora=fin + timedelta(minutes=1))

    # Exactamente 1 hora antes (13:00) -> permitido
    assert service.convertir_a_prestamo(reserva.id, ahora=inicio - timedelta(hours=1)) is True
    assert reserva.estado == EstadoReserva.CONVERTIDA



