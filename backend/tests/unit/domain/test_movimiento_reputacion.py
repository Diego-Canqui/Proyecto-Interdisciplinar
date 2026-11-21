"""Tests unitarios de dominio para MovimientoReputacion y TipoMovimientoReputacion."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.movimiento_reputacion import (
    MovimientoReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_movimiento_reputacion import (
    TipoMovimientoReputacion,
)


@pytest.mark.unit
class TestMovimientoReputacion:
    """Valida inmutabilidad, tipos e invariantes de saldo de MovimientoReputacion."""

    def test_crear_movimiento_valido_y_es_inmutable(self) -> None:
        usuario_id = uuid4()
        prestamo_id = uuid4()
        recurso_id = uuid4()
        fecha = datetime(2026, 11, 18, 13, 0, tzinfo=UTC)

        mov = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.BONIFICACION_ENTREGA_PUNTUAL,
            motivo="Entrega puntual en ventanilla",
            puntaje_anterior=500,
            variacion_puntos=10,
            puntaje_resultante=510,
            fecha_movimiento=fecha,
            numero_secuencia=1,
            prestamo_id=prestamo_id,
            recurso_id=recurso_id,
            recurso_nombre="Laptop Dell",
        )

        assert mov.usuario_id == usuario_id
        assert mov.tipo == TipoMovimientoReputacion.BONIFICACION_ENTREGA_PUNTUAL
        assert mov.variacion_puntos == 10
        assert mov.puntaje_resultante == 510
        assert mov.recurso_nombre == "Laptop Dell"

        with pytest.raises(FrozenInstanceError):
            mov.variacion_puntos = 99  # type: ignore[misc]

    def test_tipos_de_movimiento_esperados(self) -> None:
        assert {t.value for t in TipoMovimientoReputacion} == {
            "BONIFICACION_ENTREGA_PUNTUAL",
            "BONIFICACION_DEVOLUCION_PUNTUAL",
            "SANCION",
            "AMNISTIA_MENSUAL",
            "SALDO_INICIAL_HEREDADO",
        }

    def test_rechaza_puntajes_fuera_de_rango_0_1000(self) -> None:
        with pytest.raises(ValueError, match="puntaje"):
            MovimientoReputacion(
                usuario_id=uuid4(),
                tipo=TipoMovimientoReputacion.SANCION,
                motivo="Daño",
                puntaje_anterior=10,
                variacion_puntos=-20,
                puntaje_resultante=-10,
            )

        with pytest.raises(ValueError, match="puntaje"):
            MovimientoReputacion(
                usuario_id=uuid4(),
                tipo=TipoMovimientoReputacion.BONIFICACION_DEVOLUCION_PUNTUAL,
                motivo="Devolución puntual",
                puntaje_anterior=995,
                variacion_puntos=10,
                puntaje_resultante=1005,
            )

    def test_rechaza_variacion_inconsistente_con_saldos(self) -> None:
        with pytest.raises(ValueError, match="variacion"):
            MovimientoReputacion(
                usuario_id=uuid4(),
                tipo=TipoMovimientoReputacion.BONIFICACION_ENTREGA_PUNTUAL,
                motivo="Entrega puntual",
                puntaje_anterior=995,
                variacion_puntos=10,
                puntaje_resultante=1000,
            )

    def test_acepta_variacion_cero_en_tope_y_piso(self) -> None:
        mov_tope = MovimientoReputacion(
            usuario_id=uuid4(),
            tipo=TipoMovimientoReputacion.BONIFICACION_DEVOLUCION_PUNTUAL,
            motivo="Devolución puntual",
            puntaje_anterior=1000,
            variacion_puntos=0,
            puntaje_resultante=1000,
        )
        mov_piso = MovimientoReputacion(
            usuario_id=uuid4(),
            tipo=TipoMovimientoReputacion.SANCION,
            motivo="Inasistencia",
            puntaje_anterior=0,
            variacion_puntos=0,
            puntaje_resultante=0,
        )
        assert mov_tope.variacion_puntos == 0
        assert mov_piso.variacion_puntos == 0

    def test_rechaza_motivo_vacio_o_secuencia_menor_a_1(self) -> None:
        with pytest.raises(ValueError, match="motivo"):
            MovimientoReputacion(
                usuario_id=uuid4(),
                tipo=TipoMovimientoReputacion.AMNISTIA_MENSUAL,
                motivo="   ",
                puntaje_anterior=200,
                variacion_puntos=25,
                puntaje_resultante=225,
            )

        with pytest.raises(ValueError, match="secuencia"):
            MovimientoReputacion(
                usuario_id=uuid4(),
                tipo=TipoMovimientoReputacion.AMNISTIA_MENSUAL,
                motivo="Amnistía mensual",
                puntaje_anterior=200,
                variacion_puntos=25,
                puntaje_resultante=225,
                numero_secuencia=0,
            )
