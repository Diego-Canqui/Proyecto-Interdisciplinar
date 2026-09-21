from enum import Enum


class EstadoRecurso(str, Enum):
    """«enumeration» EstadoRecurso."""

    DISPONIBLE = "DISPONIBLE"
    EN_USO = "EN_USO"
    MANTENIMIENTO = "MANTENIMIENTO"
    FUERA_DE_SERVICIO = "FUERA_DE_SERVICIO"
