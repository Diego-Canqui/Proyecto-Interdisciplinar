from datetime import UTC, datetime
from uuid import uuid4

import pytest

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva


def _crear_reserva(
    *,
    inicio: datetime | None = None,
    fin: datetime | None = None,
    estado: EstadoReserva = EstadoReserva.PENDIENTE,
) -> Reserva:
    fecha_inicio = inicio or datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    fecha_fin = fin or datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    return Reserva(
        usuario_id=uuid4(),
        recurso_id=uuid4(),
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado=estado,
    )


@pytest.mark.unit
@pytest.mark.parametrize("estado", [EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA])
def test_vencer_reserva_activa_cambia_a_vencida(estado: EstadoReserva):
    reserva = _crear_reserva(estado=estado)

    reserva.vencer()

    assert reserva.estado == EstadoReserva.VENCIDA


@pytest.mark.unit
@pytest.mark.parametrize(
    "estado",
    [EstadoReserva.CANCELADA, EstadoReserva.VENCIDA, EstadoReserva.CONVERTIDA],
)
def test_vencer_reserva_en_estado_terminal_lanza_error(estado: EstadoReserva):
    reserva = _crear_reserva(estado=estado)

    with pytest.raises(ValueError, match="la reserva no se puede vencer en su estado actual"):
        reserva.vencer()

    assert reserva.estado == estado


@pytest.mark.unit
def test_limite_recogida_ventana_normal_y_corta():
    reserva_normal = _crear_reserva(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    )
    assert reserva_normal.limite_recogida() == datetime(2026, 10, 1, 10, 30, tzinfo=UTC)

    reserva_corta = _crear_reserva(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 1, 10, 20, tzinfo=UTC),
    )
    assert reserva_corta.limite_recogida() == datetime(2026, 10, 1, 10, 20, tzinfo=UTC)


@pytest.mark.unit
def test_limite_recogida_normaliza_fechas_naive_a_utc():
    reserva_naive = _crear_reserva(
        inicio=datetime(2026, 10, 1, 10, 0),  # noqa: DTZ001
        fin=datetime(2026, 10, 1, 12, 0),  # noqa: DTZ001
    )
    limite = reserva_naive.limite_recogida()
    assert limite == datetime(2026, 10, 1, 10, 30, tzinfo=UTC)
    assert limite.tzinfo == UTC
