from enum import Enum


class RolUsuario(str, Enum):
    """«enumeration» RolUsuario."""

    ESTUDIANTE = "ESTUDIANTE"
    PROFESOR = "PROFESOR"
    ADMIN = "ADMIN"
    BIBLIOTECARIO = "BIBLIOTECARIO"
