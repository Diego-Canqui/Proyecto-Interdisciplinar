"""Tests para el enum TipoSancion."""
import pytest


@pytest.mark.unit
class TestTipoSancion:
    """Tests para verificar puntos_descuento y monto_descuento por variante."""

    def test_tipo_sancion_tiene_4_valores(self):
        """TipoSancion debe tener exactamente 4 valores."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion

        miembros = list(TipoSancion)
        assert len(miembros) == 4

        assert hasattr(TipoSancion, "TARDANZA")
        assert hasattr(TipoSancion, "DANO_PARCIAL")
        assert hasattr(TipoSancion, "DANO_TOTAL")
        assert hasattr(TipoSancion, "INASISTENCIA_RESERVA")

    def test_tardanza_puntos_y_monto(self):
        """TARDANZA: -10 pts, $0."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion

        assert TipoSancion.TARDANZA.puntos_descuento == -10
        assert TipoSancion.TARDANZA.monto_descuento == 0

    def test_dano_parcial_puntos_y_monto(self):
        """DANO_PARCIAL: -30 pts, $50."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion

        assert TipoSancion.DANO_PARCIAL.puntos_descuento == -30
        assert TipoSancion.DANO_PARCIAL.monto_descuento == 50

    def test_dano_total_puntos_y_monto(self):
        """DANO_TOTAL: -100 pts, valor recurso (monto base 0, se calcula en service)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion

        assert TipoSancion.DANO_TOTAL.puntos_descuento == -100
        assert TipoSancion.DANO_TOTAL.monto_descuento == 0

    def test_inasistencia_reserva_puntos_y_monto(self):
        """INASISTENCIA_RESERVA: -15 pts, $0."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion

        assert TipoSancion.INASISTENCIA_RESERVA.puntos_descuento == -15
        assert TipoSancion.INASISTENCIA_RESERVA.monto_descuento == 0

    def test_todos_tienen_propiedades_requeridas(self):
        """Todos los valores deben tener puntos_descuento y monto_descuento."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion

        for tipo in TipoSancion:
            assert hasattr(tipo, "puntos_descuento")
            assert hasattr(tipo, "monto_descuento")
            assert isinstance(tipo.puntos_descuento, int)
            assert isinstance(tipo.monto_descuento, (int, float))
            assert tipo.puntos_descuento < 0  # Todos son descuentos (negativos)
            assert tipo.monto_descuento >= 0  # Montos no negativos


if __name__ == "__main__":
    pytest.main([__file__, "-v"])