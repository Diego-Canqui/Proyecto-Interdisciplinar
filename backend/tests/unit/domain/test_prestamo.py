from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo


def _crear_prestamo(
    *,
    inicio: datetime | None = None,
    fin: datetime | None = None,
    estado: EstadoPrestamo = EstadoPrestamo.ACTIVO,
) -> Prestamo:
    fecha_inicio = inicio or datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
    fecha_fin = fin or datetime(2026, 10, 5, 18, 0, tzinfo=UTC)
    return Prestamo(
        reserva_id=uuid4(),
        recurso_id=uuid4(),
        usuario_id=uuid4(),
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado=estado,
    )


@pytest.mark.unit
def test_creacion_prestamo_valido():
    prestamo = _crear_prestamo()
    assert prestamo.id is not None
    assert prestamo.estado == EstadoPrestamo.ACTIVO
    assert prestamo.fecha_fin > prestamo.fecha_inicio


@pytest.mark.unit
def test_creacion_con_fechas_invalidas_lanza_error():
    ahora = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="fecha_fin debe ser posterior a fecha_inicio"):
        _crear_prestamo(inicio=ahora, fin=ahora)

    with pytest.raises(ValueError, match="fecha_fin debe ser posterior a fecha_inicio"):
        _crear_prestamo(inicio=ahora, fin=ahora - timedelta(days=1))


@pytest.mark.unit
def test_iniciar_prestamo():
    prestamo = _crear_prestamo()
    prestamo.iniciar()
    assert prestamo.estado == EstadoPrestamo.ACTIVO


@pytest.mark.unit
def test_iniciar_prestamo_devuelto_o_cancelado_lanza_error():
    prestamo_devuelto = _crear_prestamo(estado=EstadoPrestamo.DEVUELTO)
    with pytest.raises(ValueError, match="No se puede iniciar"):
        prestamo_devuelto.iniciar()

    prestamo_cancelado = _crear_prestamo(estado=EstadoPrestamo.CANCELADO)
    with pytest.raises(ValueError, match="No se puede iniciar"):
        prestamo_cancelado.iniciar()


@pytest.mark.unit
def test_devolver_prestamo_a_tiempo():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
    )
    fecha_devolucion = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    dias_retraso = prestamo.devolver(fecha_devolucion)

    assert dias_retraso == 0
    assert prestamo.estado == EstadoPrestamo.DEVUELTO


@pytest.mark.unit
def test_devolver_prestamo_mismo_dia_fecha_fin():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
    )
    fecha_devolucion = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
    dias_retraso = prestamo.devolver(fecha_devolucion)

    assert dias_retraso == 0
    assert prestamo.estado == EstadoPrestamo.DEVUELTO


@pytest.mark.unit
def test_devolver_prestamo_con_retraso():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
    )
    fecha_devolucion = datetime(2026, 10, 8, 10, 0, tzinfo=UTC)
    dias_retraso = prestamo.devolver(fecha_devolucion)

    assert dias_retraso == 3
    assert prestamo.estado == EstadoPrestamo.DEVUELTO


@pytest.mark.unit
def test_devolver_prestamo_vencido_permite_retornar_dias():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.VENCIDO,
    )
    fecha_devolucion = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)
    dias_retraso = prestamo.devolver(fecha_devolucion)

    assert dias_retraso == 2
    assert prestamo.estado == EstadoPrestamo.DEVUELTO


@pytest.mark.unit
def test_devolver_prestamo_ya_devuelto_lanza_error():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.DEVUELTO)
    with pytest.raises(ValueError, match="El préstamo ya fue devuelto"):
        prestamo.devolver()


@pytest.mark.unit
def test_devolver_prestamo_cancelado_lanza_error():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.CANCELADO)
    with pytest.raises(ValueError, match="No se puede devolver un préstamo cancelado"):
        prestamo.devolver()


@pytest.mark.unit
def test_vencer_prestamo_exitoso():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )
    fecha_actual = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
    prestamo.vencer(fecha_actual)

    assert prestamo.estado == EstadoPrestamo.VENCIDO


@pytest.mark.unit
def test_vencer_prestamo_antes_de_tiempo_lanza_error():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
    )
    fecha_actual = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="aún no ha superado su fecha de finalización"):
        prestamo.vencer(fecha_actual)


@pytest.mark.unit
def test_vencer_prestamo_ya_devuelto_o_cancelado_lanza_error():
    prestamo_dev = _crear_prestamo(estado=EstadoPrestamo.DEVUELTO)
    with pytest.raises(ValueError, match="No se puede marcar como vencido"):
        prestamo_dev.vencer(datetime(2026, 10, 10, tzinfo=UTC))

    prestamo_canc = _crear_prestamo(estado=EstadoPrestamo.CANCELADO)
    with pytest.raises(ValueError, match="No se puede marcar como vencido"):
        prestamo_canc.vencer(datetime(2026, 10, 10, tzinfo=UTC))


@pytest.mark.unit
def test_solicitar_prorroga():
    fin = datetime(2026, 10, 5, 18, 0, tzinfo=UTC)
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=fin,
        estado=EstadoPrestamo.ACTIVO,
    )

    # Prórroga válida dentro del plazo
    assert prestamo.solicitar_prorroga(dias=3, fecha_actual=datetime(2026, 10, 4, tzinfo=UTC)) is True

    # Días no positivos
    assert prestamo.solicitar_prorroga(dias=0) is False
    assert prestamo.solicitar_prorroga(dias=-2) is False

    # Fuera de plazo
    assert (
        prestamo.solicitar_prorroga(dias=3, fecha_actual=datetime(2026, 10, 6, tzinfo=UTC)) is False
    )

    # En estado no activo
    prestamo.estado = EstadoPrestamo.VENCIDO
    assert prestamo.solicitar_prorroga(dias=3) is False


@pytest.mark.unit
def test_renovar_exitoso():
    fecha_inicio = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    fecha_fin = datetime(2026, 10, 5, 18, 0, tzinfo=UTC)
    prestamo = _crear_prestamo(inicio=fecha_inicio, fin=fecha_fin, estado=EstadoPrestamo.ACTIVO)

    fecha_actual = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
    prestamo.renovar(dias=5, fecha_actual=fecha_actual)

    assert prestamo.fecha_fin == fecha_fin + timedelta(days=5)


@pytest.mark.unit
def test_renovar_invalido_lanza_error():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ACTIVO,
    )

    # Días <= 0
    with pytest.raises(ValueError, match="días de renovación deben ser mayores a 0"):
        prestamo.renovar(dias=0)

    # Fuera de fecha
    with pytest.raises(ValueError, match="No se puede renovar"):
        prestamo.renovar(dias=3, fecha_actual=datetime(2026, 10, 6, tzinfo=UTC))


@pytest.mark.unit
def test_cancelar_prestamo():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.ACTIVO)
    prestamo.cancelar()
    assert prestamo.estado == EstadoPrestamo.CANCELADO

    prestamo_dev = _crear_prestamo(estado=EstadoPrestamo.DEVUELTO)
    with pytest.raises(ValueError, match="No se puede cancelar un préstamo que ya ha sido devuelto"):
        prestamo_dev.cancelar()

