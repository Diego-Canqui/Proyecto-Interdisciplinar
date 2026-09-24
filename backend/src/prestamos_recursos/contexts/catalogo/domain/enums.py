from __future__ import annotations

from enum import Enum


class EstadoRecurso(str, Enum):
    """Enumeración que representa los estados posibles de un recurso académico."""

    DISPONIBLE = "DISPONIBLE"
    EN_USO = "EN_USO"
    MANTENIMIENTO = "MANTENIMIENTO"
    FUERA_DE_SERVICIO = "FUERA_DE_SERVICIO"
