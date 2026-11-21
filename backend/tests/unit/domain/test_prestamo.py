from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo


def _crear_prestamo(
    *,
    inicio: datetime | None = None,
    fin: datetime | None = None,
    estado: EstadoPrestamo = EstadoPrestamo.POR_ENTREGAR,
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
    assert prestamo.estado == EstadoPrestamo.POR_ENTREGAR
    assert prestamo.fecha_fin > prestamo.fecha_inicio
    assert prestamo.fecha_entrega_real is None
    assert prestamo.fecha_devolucion_real is None


@pytest.mark.unit
def test_marcar_entregado_registra_fecha_entrega_real():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.POR_ENTREGAR)
    fecha_entrega = datetime(2026, 10, 1, 9, 30, tzinfo=UTC)

    prestamo.marcar_entregado(fecha_entrega)

    assert prestamo.estado == EstadoPrestamo.ENTREGADO
    assert prestamo.fecha_entrega_real == fecha_entrega
    assert prestamo.fecha_devolucion_real is None


@pytest.mark.unit
def test_marcar_entregado_sin_fecha_usa_utc_actual():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.POR_ENTREGAR)
    antes = datetime.now(UTC)

    prestamo.marcar_entregado()

    despues = datetime.now(UTC)
    assert prestamo.estado == EstadoPrestamo.ENTREGADO
    assert prestamo.fecha_entrega_real is not None
    assert prestamo.fecha_entrega_real.tzinfo == UTC
    assert antes <= prestamo.fecha_entrega_real <= despues


@pytest.mark.unit
def test_marcar_entregado_no_por_entregar_lanza_error():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.ENTREGADO)
    with pytest.raises(ValueError, match="POR_ENTREGAR"):
        prestamo.marcar_entregado()
    assert prestamo.fecha_entrega_real is None


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
    assert prestamo.estado == EstadoPrestamo.POR_ENTREGAR


@pytest.mark.unit
def test_iniciar_prestamo_devuelto_o_cancelado_lanza_error():
    prestamo_devuelto = _crear_prestamo(estado=EstadoPrestamo.DEVUELTO)
    with pytest.raises(ValueError, match="No se puede iniciar"):
        prestamo_devuelto.iniciar()

    prestamo_cancelado = _crear_prestamo(estado=EstadoPrestamo.CANCELADO)
    with pytest.raises(ValueError, match="No se puede iniciar"):
        prestamo_cancelado.iniciar()


@pytest.mark.unit
def test_limite_recogida_ventana_normal_y_corta():
    prestamo_normal = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    )
    assert prestamo_normal.limite_recogida() == datetime(2026, 10, 1, 10, 30, tzinfo=UTC)

    prestamo_corto = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 1, 10, 20, tzinfo=UTC),
    )
    assert prestamo_corto.limite_recogida() == datetime(2026, 10, 1, 10, 20, tzinfo=UTC)


@pytest.mark.unit
def test_devolver_prestamo_a_tiempo():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    fecha_devolucion = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    dias_retraso = prestamo.devolver(fecha_devolucion)

    assert dias_retraso == 0
    assert prestamo.estado == EstadoPrestamo.DEVUELTO
    assert prestamo.fecha_devolucion_real == fecha_devolucion


@pytest.mark.unit
def test_devolver_prestamo_mismo_dia_fecha_fin():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
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
        estado=EstadoPrestamo.ENTREGADO,
    )
    fecha_devolucion = datetime(2026, 10, 8, 10, 0, tzinfo=UTC)
    dias_retraso = prestamo.devolver(fecha_devolucion)

    assert dias_retraso == 3
    assert prestamo.estado == EstadoPrestamo.DEVUELTO


@pytest.mark.unit
def test_devolver_prestamo_vencido_es_valido():
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
    with pytest.raises(ValueError, match="ya fue devuelto"):
        prestamo.devolver()


@pytest.mark.unit
def test_devolver_prestamo_cancelado_lanza_error():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.CANCELADO)
    with pytest.raises(ValueError, match="cancelado"):
        prestamo.devolver()


@pytest.mark.unit
def test_devolver_prestamo_por_entregar_lanza_error():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.POR_ENTREGAR)
    with pytest.raises(ValueError, match="POR_ENTREGAR"):
        prestamo.devolver()


@pytest.mark.unit
def test_vencer_prestamo_entregado_exitoso():
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=datetime(2026, 10, 5, 18, 0, tzinfo=UTC),
        estado=EstadoPrestamo.ENTREGADO,
    )
    fecha_actual = datetime(2026, 10, 5, 18, 1, tzinfo=UTC)
    prestamo.vencer(fecha_actual)

    assert prestamo.estado == EstadoPrestamo.VENCIDO


@pytest.mark.unit
def test_vencer_prestamo_en_limite_o_antes_lanza_error():
    fin = datetime(2026, 10, 5, 18, 0, tzinfo=UTC)
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=fin,
        estado=EstadoPrestamo.ENTREGADO,
    )
    with pytest.raises(ValueError, match="aún no ha superado su fecha de finalización"):
        prestamo.vencer(datetime(2026, 10, 4, 12, 0, tzinfo=UTC))

    with pytest.raises(ValueError, match="aún no ha superado su fecha de finalización"):
        prestamo.vencer(fin)


@pytest.mark.unit
@pytest.mark.parametrize(
    "estado",
    [
        EstadoPrestamo.POR_ENTREGAR,
        EstadoPrestamo.DEVUELTO,
        EstadoPrestamo.CANCELADO,
        EstadoPrestamo.VENCIDO,
    ],
)
def test_vencer_prestamo_no_entregado_lanza_error(estado: EstadoPrestamo):
    prestamo = _crear_prestamo(estado=estado)
    with pytest.raises(ValueError, match="No se puede marcar como vencido"):
        prestamo.vencer(datetime(2026, 10, 10, tzinfo=UTC))


@pytest.mark.unit
def test_prestamo_sin_metodos_prorroga_ni_renovar():
    assert not hasattr(Prestamo, "solicitar_prorroga")
    assert not hasattr(Prestamo, "renovar")


@pytest.mark.unit
def test_es_devolucion_puntual_antes_en_y_despues_de_fecha_fin():
    fecha_fin = datetime(2026, 10, 5, 14, 0, tzinfo=UTC)
    prestamo = _crear_prestamo(
        inicio=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        fin=fecha_fin,
        estado=EstadoPrestamo.ENTREGADO,
    )

    # Antes de la hora límite -> puntual
    assert prestamo.es_devolucion_puntual(datetime(2026, 10, 5, 13, 59, tzinfo=UTC)) is True
    # Exactamente a la hora límite -> puntual
    assert prestamo.es_devolucion_puntual(datetime(2026, 10, 5, 14, 0, tzinfo=UTC)) is True
    # Mismo día después de la hora límite -> NO puntual, pero 0 días de retraso
    mismo_dia_tarde = datetime(2026, 10, 5, 16, 0, tzinfo=UTC)
    assert prestamo.es_devolucion_puntual(mismo_dia_tarde) is False
    assert prestamo.calcular_dias_retraso(mismo_dia_tarde) == 0

    # Al devolver usando fecha_devolucion_real, sin argumento usa fecha_devolucion_real
    prestamo.devolver(mismo_dia_tarde)
    assert prestamo.es_devolucion_puntual() is False


@pytest.mark.unit
def test_cancelar_prestamo():
    prestamo = _crear_prestamo(estado=EstadoPrestamo.POR_ENTREGAR)
    prestamo.cancelar()
    assert prestamo.estado == EstadoPrestamo.CANCELADO

    prestamo_dev = _crear_prestamo(estado=EstadoPrestamo.DEVUELTO)
    with pytest.raises(ValueError, match="No se puede cancelar un préstamo que ya ha sido devuelto"):
        prestamo_dev.cancelar()


@pytest.mark.unit
@pytest.mark.parametrize(
    "estado",
    [EstadoPrestamo.ENTREGADO, EstadoPrestamo.VENCIDO, EstadoPrestamo.CANCELADO],
)
def test_cancelar_prestamo_no_por_entregar_lanza_error(estado: EstadoPrestamo):
    prestamo = _crear_prestamo(estado=estado)
    with pytest.raises(
        ValueError,
        match="Solo se pueden cancelar préstamos pendientes de entrega física \\(POR_ENTREGAR\\)",
    ):
        prestamo.cancelar()
