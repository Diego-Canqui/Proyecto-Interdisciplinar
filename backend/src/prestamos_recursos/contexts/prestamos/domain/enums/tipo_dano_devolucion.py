from enum import Enum


class TipoDanoDevolucion(str, Enum):
    """Clasificación del daño físico observado al devolver un recurso."""

    NINGUNO = "NINGUNO"
    DANO_PARCIAL = "DANO_PARCIAL"
    DANO_TOTAL = "DANO_TOTAL"
