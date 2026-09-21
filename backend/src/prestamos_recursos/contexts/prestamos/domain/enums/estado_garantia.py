from enum import Enum


class EstadoGarantia(str, Enum):
    """«enumeration» EstadoGarantia."""

    PENDIENTE = "PENDIENTE"
    REGISTRADA = "REGISTRADA"
    LIBERADA = "LIBERADA"
    RETENIDA = "RETENIDA"
