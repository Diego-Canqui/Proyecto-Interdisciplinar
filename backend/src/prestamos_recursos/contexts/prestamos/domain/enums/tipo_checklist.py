from enum import Enum


class TipoChecklist(str, Enum):
    """«enumeration» TipoChecklist."""

    ESTADO_INICIAL = "ESTADO_INICIAL"
    ESTADO_DEVOLUCION = "ESTADO_DEVOLUCION"
