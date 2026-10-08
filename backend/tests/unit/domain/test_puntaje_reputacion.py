"""Tests para el Value Object PuntajeReputacion."""
import pytest


@pytest.mark.unit
class TestPuntajeReputacion:
    """Tests para validar rango 0..1000 e inmutabilidad."""

    def test_valor_valido_en_rango(self):
        """Valores en rango 0..1000 deben ser aceptados."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        # Límite inferior
        p0 = PuntajeReputacion(puntos=0)
        assert p0.puntos == 0

        # Valor medio
        p500 = PuntajeReputacion(puntos=500)
        assert p500.puntos == 500

        # Límite superior
        p1000 = PuntajeReputacion(puntos=1000)
        assert p1000.puntos == 1000

    def test_valor_fuera_de_rango_superior_lanza_valueerror(self):
        """Puntaje > 1000 debe lanzar ValueError."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        with pytest.raises(ValueError, match="rango.*0.*1000|0.*1000.*rango|puntos.*1000|1000.*puntos"):
            PuntajeReputacion(puntos=1001)

        with pytest.raises(ValueError):
            PuntajeReputacion(puntos=2000)

    def test_valor_fuera_de_rango_inferior_lanza_valueerror(self):
        """Puntaje < 0 debe lanzar ValueError."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        with pytest.raises(ValueError, match="rango.*0.*1000|0.*1000.*rango|puntos.*0|0.*puntos|negativo"):
            PuntajeReputacion(puntos=-1)

        with pytest.raises(ValueError):
            PuntajeReputacion(puntos=-100)

    def test_sumar_devuelve_nueva_instancia(self):
        """sumar() debe devolver una nueva instancia (inmutabilidad)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        original = PuntajeReputacion(puntos=100)
        resultado = original.sumar(50)

        # Debe ser una instancia distinta
        assert resultado is not original
        # Valor correcto
        assert resultado.puntos == 150
        # Original inalterado
        assert original.puntos == 100

    def test_restar_devuelve_nueva_instancia(self):
        """restar() debe devolver una nueva instancia (inmutabilidad)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        original = PuntajeReputacion(puntos=100)
        resultado = original.restar(30)

        # Debe ser una instancia distinta
        assert resultado is not original
        # Valor correcto
        assert resultado.puntos == 70
        # Original inalterado
        assert original.puntos == 100

    def test_restar_no_puede_bajar_de_cero(self):
        """restar() no debe permitir valores negativos (clamp a 0)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        original = PuntajeReputacion(puntos=50)
        resultado = original.restar(100)

        assert resultado.puntos == 0

    def test_sumar_valida_rango_en_nueva_instancia(self):
        """sumar() debe validar rango en la nueva instancia."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        original = PuntajeReputacion(puntos=950)
        with pytest.raises(ValueError):
            original.sumar(100)  # 1050 > 1000

    def test_restar_valida_rango_en_nueva_instancia(self):
        """restar() debe validar rango en la nueva instancia (aunque clamp a 0)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        original = PuntajeReputacion(puntos=50)
        resultado = original.restar(100)  # Debería dar 0, no negativo
        assert resultado.puntos == 0

    def test_es_valido(self):
        """es_valido() debe retornar True para valores >= 0."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        assert PuntajeReputacion(puntos=0).es_valido() is True
        assert PuntajeReputacion(puntos=500).es_valido() is True
        assert PuntajeReputacion(puntos=1000).es_valido() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])