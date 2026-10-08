"""Tests para el enum NivelReputacion."""
import pytest


@pytest.mark.unit
class TestNivelReputacion:
    """Tests para verificar los 4 valores del enum NivelReputacion."""

    def test_nivel_reputacion_tiene_exactamente_4_valores(self):
        """NivelReputacion debe tener exactamente 4 valores: BAJO, NORMAL, BUENO, EXCELENTE."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion

        miembros = list(NivelReputacion)
        assert len(miembros) == 4

        assert hasattr(NivelReputacion, "BAJO")
        assert hasattr(NivelReputacion, "NORMAL")
        assert hasattr(NivelReputacion, "BUENO")
        assert hasattr(NivelReputacion, "EXCELENTE")

    def test_valores_exactos(self):
        """Verificar valores exactos de cada nivel."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion

        assert NivelReputacion.BAJO == "BAJO"
        assert NivelReputacion.NORMAL == "NORMAL"
        assert NivelReputacion.BUENO == "BUENO"
        assert NivelReputacion.EXCELENTE == "EXCELENTE"

    def test_nivel_reputacion_es_str_enum(self):
        """NivelReputacion debe ser un str Enum."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion

        assert issubclass(NivelReputacion, str)
        assert isinstance(NivelReputacion.BAJO, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])