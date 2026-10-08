"""Tests para la entidad Sancion."""
import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion


@pytest.mark.unit
class TestSancion:
    """Tests para Sancion (Entity, no Aggregate Root)."""

    def test_no_hereda_de_baseentity(self):
        """Sancion no debe heredar de BaseEntity."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.shared.base_entity import BaseEntity

        # Verificar que Sancion no es subclase de BaseEntity
        assert not issubclass(Sancion, BaseEntity)

    def test_aplicar_marca_activa_true(self):
        """aplicar() debe marcar activa=True."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Devolución tardía",
            fecha_aplicacion=datetime.now(),
            activa=False,
        )

        sancion.aplicar()

        assert sancion.activa is True

    def test_calcular_descuento_retorna_puntos_descuento(self):
        """calcular_descuento() debe retornar puntos_descuento."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Devolución tardía",
            fecha_aplicacion=datetime.now(),
            activa=False,
        )

        assert sancion.calcular_descuento() == -10

    def test_generar_cobro_true_si_monto_gt_cero(self):
        """generar_cobro() debe ser True si monto_descuento > 0."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        sancion_con_monto = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=datetime.now(),
            activa=False,
        )

        sancion_sin_monto = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=datetime.now(),
            activa=False,
        )

        assert sancion_con_monto.generar_cobro() is True
        assert sancion_sin_monto.generar_cobro() is False

    def test_atributos_completos(self):
        """Sancion debe tener todos los atributos requeridos."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        id_val = uuid4()
        tipo = TipoSancion.DANO_TOTAL
        puntos = -100
        monto = Decimal("0")
        motivo = "Daño total"
        fecha = datetime.now()
        activa = True

        sancion = Sancion(
            id=id_val,
            tipo=tipo,
            puntos_descuento=puntos,
            monto_descuento=monto,
            motivo=motivo,
            fecha_aplicacion=fecha,
            activa=activa,
        )

        assert sancion.id == id_val
        assert sancion.tipo == tipo
        assert sancion.puntos_descuento == puntos
        assert sancion.monto_descuento == monto
        assert sancion.motivo == motivo
        assert sancion.fecha_aplicacion == fecha
        assert sancion.activa == activa


if __name__ == "__main__":
    pytest.main([__file__, "-v"])