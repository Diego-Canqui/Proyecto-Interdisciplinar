from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo


class PrestamoRepository(ABC):
    """«Repository» PrestamoRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, prestamo: Prestamo) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> Prestamo | None:
        ...

    @abstractmethod
    def obtener_activos(self) -> list[Prestamo]:
        ...

    @abstractmethod
    def obtener_por_usuario(self, id_usuario: UUID) -> list[Prestamo]:
        ...
