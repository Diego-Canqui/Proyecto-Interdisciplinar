from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.reservas.application.reserva_service import ReservaService
from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva


class FakeReservaRepository:
    def __init__(self, reservas: list[Reserva] | None = None):
        self.reservas = list(reservas) if reservas is not None else []
        self.guardados: list[Reserva] = []

    def obtener_por_id(self, id_reserva: UUID) -> Reserva | None:
        return next((r for r in self.reservas if r.id == id_reserva), None)

    def obtener_todas(self) -> list[Reserva]:
        return list(self.reservas)

    def obtener_por_usuario(self, id_usuario: UUID) -> list[Reserva]:
        return [r for r in self.reservas if r.usuario_id == id_usuario]

    def obtener_activas_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        return [
            r
            for r in self.reservas
            if r.recurso_id == id_recurso
            and r.estado in {EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA}
        ]

    def obtener_cola_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        return [
            r
            for r in self.reservas
            if r.recurso_id == id_recurso and r.estado == EstadoReserva.PENDIENTE
        ]

    def guardar(self, reserva: Reserva) -> None:
        self.guardados.append(reserva)
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
        return []


class FakeRecursoRepository:
    def __init__(self, estado=EstadoRecurso.DISPONIBLE):
        self.recurso = SimpleNamespace(estado=estado)

    def obtener_por_id(self, id_recurso):
        return self.recurso

    def actualizar_estado(self, id_recurso, estado):
        self.recurso.estado = estado


class FakeReputacionService:
    def __init__(self):
        self.sanciones: list[tuple[UUID, TipoSancion, str]] = []
        self.sanciones_detalle: list[dict] = []

    def aplicar_sancion(self, usuario_id: UUID, tipo: TipoSancion, motivo: str, **kwargs):
        self.sanciones.append((usuario_id, tipo, motivo))
        self.sanciones_detalle.append(
            {
                "usuario_id": usuario_id,
                "tipo": tipo,
                "motivo": motivo,
                **kwargs,
            }
        )
        return SimpleNamespace(usuario_id=usuario_id, tipo=tipo, motivo=motivo)

    def consultar_puntaje_lectura(self, usuario_id: UUID) -> int:
        return 500

    def consultar_elegibilidad_lectura(self, usuario_id: UUID):
        return SimpleNamespace(elegible=True, razon=None)


def _make_prestamo_service():
    return PrestamoService(
        FakePrestamoRepository(),
        SimpleNamespace(),
        SimpleNamespace(),
        catalogo_service=FakeRecursoRepository(),
    )


def test_pendiente_pasada_fecha_fin_pasa_a_vencida_sin_sancion_en_cola_y_consultas():
    """RF-12, CL-6: PENDIENTE pasada fecha_fin -> VENCIDA sin sanción y no aparece en cola."""
    u_id = uuid4()
    r_id = uuid4()
    ahora = datetime.now(UTC)
    vencida = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=ahora - timedelta(hours=3),
        fecha_fin=ahora - timedelta(minutes=1),
        estado=EstadoReserva.PENDIENTE,
    )
    vigente = Reserva(
        usuario_id=uuid4(),
        recurso_id=r_id,
        fecha_inicio=ahora + timedelta(hours=1),
        fecha_fin=ahora + timedelta(hours=3),
        estado=EstadoReserva.PENDIENTE,
    )
    repo = FakeReservaRepository([vencida, vigente])
    reputacion = FakeReputacionService()
    service = ReservaService(repo, _make_prestamo_service(), reputacion_service=reputacion)

    cola = service.obtener_cola_espera(r_id)

    assert len(cola) == 1
    assert cola[0].id == vigente.id
    assert vencida.estado == EstadoReserva.VENCIDA
    assert reputacion.sanciones == []


def test_confirmada_pasado_limite_recogida_pasa_a_vencida_con_sancion_unica_sin_promover_cola():
    """RF-12, RF-13, CL-7, CL-10: CONFIRMADA expirada -> VENCIDA + INASISTENCIA_RESERVA única, sin promover cola."""
    u_confirmado = uuid4()
    u_cola = uuid4()
    r_id = uuid4()
    ahora = datetime.now(UTC)

    confirmada_expirada = Reserva(
        usuario_id=u_confirmado,
        recurso_id=r_id,
        fecha_inicio=ahora - timedelta(minutes=31),
        fecha_fin=ahora + timedelta(hours=2),
        estado=EstadoReserva.CONFIRMADA,
    )
    pendiente_en_cola = Reserva(
        usuario_id=u_cola,
        recurso_id=r_id,
        fecha_inicio=ahora - timedelta(minutes=31),
        fecha_fin=ahora + timedelta(hours=2),
        estado=EstadoReserva.PENDIENTE,
    )
    repo = FakeReservaRepository([confirmada_expirada, pendiente_en_cola])
    reputacion = FakeReputacionService()
    service = ReservaService(repo, _make_prestamo_service(), reputacion_service=reputacion)

    # Primera consulta: sincroniza
    todas = service.obtener_todas()
    assert confirmada_expirada.estado == EstadoReserva.VENCIDA
    assert pendiente_en_cola.estado == EstadoReserva.PENDIENTE  # No se promueve (CL-10)
    assert len(reputacion.sanciones) == 1
    assert reputacion.sanciones[0][0] == u_confirmado
    assert reputacion.sanciones[0][1] == TipoSancion.INASISTENCIA_RESERVA
    assert len(todas) == 2

    # Consultas repetidas: idempotentes (RNF-3, RF-13)
    service.obtener_por_usuario(u_confirmado)
    service.obtener_reserva(confirmada_expirada.id)
    assert service.contar_reservas_activas_usuario(u_confirmado) == 0
    assert len(reputacion.sanciones) == 1


def test_confirmada_en_limite_exacto_no_vence_y_puede_convertirse():
    """RF-14: en el límite exacto (inicio + 30m) aún no vence y puede convertirse."""
    u_id = uuid4()
    r_id = uuid4()
    inicio = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)
    fin = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    reserva = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
        estado=EstadoReserva.CONFIRMADA,
    )
    repo = FakeReservaRepository([reserva])
    reputacion = FakeReputacionService()
    service = ReservaService(repo, _make_prestamo_service(), reputacion_service=reputacion)

    assert service.convertir_a_prestamo(reserva.id, ahora=inicio + timedelta(minutes=30)) is True
    assert reserva.estado == EstadoReserva.CONVERTIDA
    assert reputacion.sanciones == []


def test_convertir_a_prestamo_despues_de_expiracion_persiste_vencida_y_sancion_unica():
    """RF-14, CL-9: convertir después de min(inicio+30m, fin) persiste VENCIDA + sanción y rechaza."""
    u_id = uuid4()
    r_id = uuid4()
    inicio = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)
    fin = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    reserva = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
        estado=EstadoReserva.CONFIRMADA,
    )
    repo = FakeReservaRepository([reserva])
    reputacion = FakeReputacionService()
    service = ReservaService(repo, _make_prestamo_service(), reputacion_service=reputacion)

    with pytest.raises(ValueError, match="expiró"):
        service.convertir_a_prestamo(reserva.id, ahora=inicio + timedelta(minutes=31))

    assert reserva.estado == EstadoReserva.VENCIDA
    assert len(reputacion.sanciones) == 1
    assert reputacion.sanciones[0][1] == TipoSancion.INASISTENCIA_RESERVA

    # Segundo intento ya encuentra estado terminal VENCIDA -> no duplica sanción
    assert service.convertir_a_prestamo(reserva.id, ahora=inicio + timedelta(minutes=35)) is False
    assert len(reputacion.sanciones) == 1


def test_reserva_corta_usa_fecha_fin_como_limite_recogida():
    """CL-2/RF-14: si duración < 30m, limite_recogida es fecha_fin."""
    u_id = uuid4()
    r_id = uuid4()
    inicio = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)
    fin = datetime(2026, 11, 2, 14, 20, tzinfo=UTC)
    reserva = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=inicio,
        fecha_fin=fin,
        estado=EstadoReserva.CONFIRMADA,
    )
    repo = FakeReservaRepository([reserva])
    reputacion = FakeReputacionService()
    service = ReservaService(repo, _make_prestamo_service(), reputacion_service=reputacion)

    with pytest.raises(ValueError, match="expiró"):
        service.convertir_a_prestamo(reserva.id, ahora=fin + timedelta(minutes=1))

    assert reserva.estado == EstadoReserva.VENCIDA
    assert len(reputacion.sanciones) == 1


def test_confirmada_expirada_propaga_referencias_y_recurso_nombre_a_sancion():
    """T4 / RF-01: al expirar CONFIRMADA, pasa reserva_id, recurso_id y recurso_nombre."""
    u_id = uuid4()
    r_id = uuid4()
    ahora = datetime.now(UTC)
    reserva = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=ahora - timedelta(minutes=31),
        fecha_fin=ahora + timedelta(hours=2),
        estado=EstadoReserva.CONFIRMADA,
    )
    repo = FakeReservaRepository([reserva])
    reputacion = FakeReputacionService()
    catalogo = SimpleNamespace(
        obtener_por_id=lambda recurso_id: SimpleNamespace(
            id=recurso_id,
            estado=EstadoRecurso.DISPONIBLE,
            nombre="Microscopio Olympus CX23",
        )
    )
    service = ReservaService(
        repo,
        _make_prestamo_service(),
        reputacion_service=reputacion,
        catalogo_service=catalogo,
    )

    service.obtener_todas()

    assert reserva.estado == EstadoReserva.VENCIDA
    assert len(reputacion.sanciones_detalle) == 1
    assert reputacion.sanciones_detalle[0] == {
        "usuario_id": u_id,
        "tipo": TipoSancion.INASISTENCIA_RESERVA,
        "motivo": "Inasistencia a recogida de reserva",
        "reserva_id": reserva.id,
        "recurso_id": r_id,
        "recurso_nombre": "Microscopio Olympus CX23",
    }


def test_confirmada_expirada_tolera_catalogo_fallido_y_doble_reputacion_sin_kwargs():
    """T4: tolera fallo/ausencia de catálogo y dobles de reputación sin kwargs nuevos."""
    u_id = uuid4()
    r_id = uuid4()
    ahora = datetime.now(UTC)
    reserva = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=ahora - timedelta(minutes=31),
        fecha_fin=ahora + timedelta(hours=2),
        estado=EstadoReserva.CONFIRMADA,
    )

    # Caso 1: catálogo lanza excepción -> recurso_nombre=None sin romper sincronización
    reputacion_detalle = FakeReputacionService()

    def _falla_catalogo(_recurso_id):
        raise RuntimeError("Catálogo no disponible")

    service_catalogo_roto = ReservaService(
        FakeReservaRepository([reserva]),
        _make_prestamo_service(),
        reputacion_service=reputacion_detalle,
        catalogo_service=SimpleNamespace(obtener_por_id=_falla_catalogo),
    )
    service_catalogo_roto.obtener_todas()
    assert reserva.estado == EstadoReserva.VENCIDA
    assert reputacion_detalle.sanciones_detalle[0]["recurso_nombre"] is None
    assert reputacion_detalle.sanciones_detalle[0]["reserva_id"] == reserva.id
    assert reputacion_detalle.sanciones_detalle[0]["recurso_id"] == r_id

    # Caso 2: doble de reputación con firma mínima (sin **kwargs) -> no lanza TypeError
    reserva_2 = Reserva(
        usuario_id=u_id,
        recurso_id=r_id,
        fecha_inicio=ahora - timedelta(minutes=31),
        fecha_fin=ahora + timedelta(hours=2),
        estado=EstadoReserva.CONFIRMADA,
    )
    llamadas = []

    class ReputacionFirmaMinima:
        def aplicar_sancion(self, usuario_id, tipo, motivo):
            llamadas.append((usuario_id, tipo, motivo))

    service_doble_minimo = ReservaService(
        FakeReservaRepository([reserva_2]),
        _make_prestamo_service(),
        reputacion_service=ReputacionFirmaMinima(),
        catalogo_service=SimpleNamespace(
            obtener_por_id=lambda rid: SimpleNamespace(
                id=rid, estado=EstadoRecurso.DISPONIBLE, nombre="Osciloscopio"
            )
        ),
    )
    service_doble_minimo.obtener_todas()
    assert reserva_2.estado == EstadoReserva.VENCIDA
    assert llamadas == [(u_id, TipoSancion.INASISTENCIA_RESERVA, "Inasistencia a recogida de reserva")]
