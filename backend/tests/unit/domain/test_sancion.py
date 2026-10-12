"""Tests para la entidad Sancion."""
import pytest
from datetime import UTC, datetime, timedelta
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

        ahora = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Devolución tardía",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=2),
            activa=False,
        )

        sancion.aplicar()

        assert sancion.activa is True

    def test_calcular_descuento_retorna_puntos_descuento(self):
        """calcular_descuento() debe retornar puntos_descuento."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        ahora = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Devolución tardía",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=2),
            activa=False,
        )

        assert sancion.calcular_descuento() == -10

    def test_generar_cobro_no_existe(self):
        """RF-09: la deuda es informativa (pago material externo); Sancion no ofrece generar_cobro."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        assert not hasattr(Sancion, "generar_cobro")

    def test_atributos_completos(self):
        """Sancion debe tener todos los atributos requeridos (incluida fecha_fin)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        id_val = uuid4()
        tipo = TipoSancion.DANO_TOTAL
        puntos = -100
        monto = Decimal("0")
        motivo = "Daño total"
        fecha = datetime.now(UTC)
        fecha_fin_val = fecha + timedelta(days=60)
        activa = True

        sancion = Sancion(
            id=id_val,
            tipo=tipo,
            puntos_descuento=puntos,
            monto_descuento=monto,
            motivo=motivo,
            fecha_aplicacion=fecha,
            fecha_fin=fecha_fin_val,
            activa=activa,
        )

        assert sancion.id == id_val
        assert sancion.tipo == tipo
        assert sancion.puntos_descuento == puntos
        assert sancion.monto_descuento == monto
        assert sancion.motivo == motivo
        assert sancion.fecha_aplicacion == fecha
        assert sancion.fecha_fin == fecha_fin_val
        assert sancion.activa == activa


@pytest.mark.unit
class TestSancionEstaVigente:
    """Tests para esta_vigente(): vigencia ESTRICTA (activa and fecha_fin > ahora, RF-02)."""

    def test_vigente_si_activa_y_fecha_fin_posterior(self):
        """activa=True y fecha_fin > ahora → vigente (bloquea)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        ahora = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=30),
            activa=True,
        )

        assert sancion.esta_vigente(ahora) is True

    def test_no_vigente_si_fecha_fin_igual_a_ahora(self):
        """Vigencia ESTRICTA: fecha_fin == ahora → ya expirada (caso límite 7, RF-02)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        ahora = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=ahora - timedelta(days=1),
            fecha_fin=ahora,
            activa=True,
        )

        assert sancion.esta_vigente(ahora) is False

    def test_no_vigente_si_fecha_fin_pasada(self):
        """fecha_fin < ahora → expirada, deja de bloquear la elegibilidad (RF-02)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        ahora = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=ahora - timedelta(days=31),
            fecha_fin=ahora - timedelta(seconds=1),
            activa=True,
        )

        assert sancion.esta_vigente(ahora) is False

    def test_no_vigente_si_inactiva_aun_con_fecha_fin_futura(self):
        """activa=False → nunca vigente aunque fecha_fin sea futura."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        ahora = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=10),
            activa=False,
        )

        assert sancion.esta_vigente(ahora) is False

    def test_gracia_tardanza_no_bloquea_nunca(self):
        """Gracia de TARDANZA (fecha_fin = fecha_aplicacion): no bloquea ni en su instante (RF-04)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        instante = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Retraso de 1 día",
            fecha_aplicacion=instante,
            fecha_fin=instante,  # Gracia de 1 día: expira de inmediato
            activa=True,
        )

        # Ni en su instante de creación (vigencia estricta) ni después
        assert sancion.esta_vigente(instante) is False
        assert sancion.esta_vigente(instante + timedelta(seconds=1)) is False

    def test_vigente_normaliza_fecha_fin_naive(self):
        """fecha_fin naive se normaliza a UTC (patrón de ExcepcionAcademica.es_vigente)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        ahora = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.INASISTENCIA_RESERVA,
            puntos_descuento=-15,
            monto_descuento=Decimal("0"),
            motivo="No recogió la reserva",
            fecha_aplicacion=ahora,
            fecha_fin=(ahora + timedelta(hours=1)).replace(tzinfo=None),  # naive
            activa=True,
        )

        assert sancion.esta_vigente(ahora) is True

    def test_vigente_normaliza_ahora_naive(self):
        """ahora naive se normaliza a UTC para comparar con fecha_fin aware."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        ahora = datetime.now(UTC)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_TOTAL,
            puntos_descuento=-100,
            monto_descuento=Decimal("1200"),
            motivo="Recurso destruido",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=60),
            activa=True,
        )

        assert sancion.esta_vigente(ahora.replace(tzinfo=None)) is True

    def test_vigente_sin_ahora_usa_instante_actual(self):
        """esta_vigente() sin argumento evalúa contra el instante actual (aware UTC)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Retraso de 2 días",
            fecha_aplicacion=datetime.now(UTC),
            fecha_fin=datetime.now(UTC) + timedelta(days=2),
            activa=True,
        )

        assert sancion.esta_vigente() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
