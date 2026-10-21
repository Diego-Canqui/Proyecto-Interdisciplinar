"""Tests para el enum RolUsuario."""
import pytest


@pytest.mark.unit
class TestRolUsuario:
    """Tests para verificar los valores exactos del enum RolUsuario."""

    def test_rol_usuario_tiene_exactamente_5_valores_ddd(self):
        """RolUsuario debe tener exactamente los 5 valores DDD especificados."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario

        # Verificar que existen los 5 valores correctos
        assert hasattr(RolUsuario, "ESTUDIANTE")
        assert hasattr(RolUsuario, "DOCENTE")
        assert hasattr(RolUsuario, "PERSONAL_ADMINISTRATIVO")
        assert hasattr(RolUsuario, "GESTOR_ALMACEN")
        assert hasattr(RolUsuario, "ADMINISTRADOR_SISTEMA")

        # Verificar valores exactos
        assert RolUsuario.ESTUDIANTE == "ESTUDIANTE"
        assert RolUsuario.DOCENTE == "DOCENTE"
        assert RolUsuario.PERSONAL_ADMINISTRATIVO == "PERSONAL_ADMINISTRATIVO"
        assert RolUsuario.GESTOR_ALMACEN == "GESTOR_ALMACEN"
        assert RolUsuario.ADMINISTRADOR_SISTEMA == "ADMINISTRADOR_SISTEMA"

        # Verificar que NO existen los valores eliminados
        assert not hasattr(RolUsuario, "PROFESOR")
        assert not hasattr(RolUsuario, "ADMIN")
        assert not hasattr(RolUsuario, "BIBLIOTECARIO")

    def test_rol_usuario_solo_tiene_5_miembros(self):
        """RolUsuario debe tener exactamente 5 miembros."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario

        miembros = list(RolUsuario)
        assert len(miembros) == 5

    def test_rol_usuario_es_str_enum(self):
        """RolUsuario debe ser un str Enum para compatibilidad con BD."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario

        assert issubclass(RolUsuario, str)
        assert isinstance(RolUsuario.ESTUDIANTE, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])