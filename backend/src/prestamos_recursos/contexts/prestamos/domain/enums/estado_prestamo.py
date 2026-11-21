from enum import Enum


class EstadoPrestamo(str, Enum):
    """«enumeration» EstadoPrestamo."""

    POR_ENTREGAR = "POR_ENTREGAR"
    ENTREGADO = "ENTREGADO"
    DEVUELTO = "DEVUELTO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"
