from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion


class SancionRepository(ABC):
    """«Repository» SancionRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, sancion: Sancion) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> Sancion | None:
        ...
