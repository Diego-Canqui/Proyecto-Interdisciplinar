from enum import Enum


class NivelReputacion(str, Enum):
    """«enumeration» NivelReputacion."""

    BAJO = "BAJO"
    NORMAL = "NORMAL"
    BUENO = "BUENO"
    EXCELENTE = "EXCELENTE"

    @property
    def limite_operaciones(self) -> int:
        """Límite de operaciones activas simultáneas permitido (RF-04)."""
        _LIMITES = {
            NivelReputacion.BAJO: 1,
            NivelReputacion.NORMAL: 2,
            NivelReputacion.BUENO: 3,
            NivelReputacion.EXCELENTE: 5,
        }
        return _LIMITES[self]
