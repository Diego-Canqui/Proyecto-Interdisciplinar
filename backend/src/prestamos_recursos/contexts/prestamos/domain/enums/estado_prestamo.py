from enum import Enum


class EstadoPrestamo(str, Enum):
    """«enumeration» EstadoPrestamo."""

    ACTIVO = "ACTIVO"
    DEVUELTO = "DEVUELTO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"
