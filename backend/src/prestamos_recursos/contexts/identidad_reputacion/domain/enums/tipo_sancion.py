from enum import Enum


class TipoSancion(str, Enum):
    """«enumeration» TipoSancion."""

    TARDANZA = "TARDANZA"
    DANO_PARCIAL = "DANO_PARCIAL"
    DANO_TOTAL = "DANO_TOTAL"
    INASISTENCIA_RESERVA = "INASISTENCIA_RESERVA"
