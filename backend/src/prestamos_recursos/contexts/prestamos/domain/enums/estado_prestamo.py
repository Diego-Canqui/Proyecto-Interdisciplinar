from enum import Enum


class EstadoPrestamo(str, Enum):
    """«enumeration» EstadoPrestamo."""

    ACTIVO = "ACTIVO"
    ENTREGADO = "ENTREGADO"
    DEVUELTO = "DEVUELTO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"
