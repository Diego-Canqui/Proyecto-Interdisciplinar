from enum import Enum


class EstadoReserva(str, Enum):
    """«enumeration» EstadoReserva."""

    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    VENCIDA = "VENCIDA"
    CONVERTIDA = "CONVERTIDA"
