from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.prestamos.domain.entities.garantia import Garantia


class GarantiaRepository(ABC):
    """«Repository» GarantiaRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, garantia: Garantia) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> Garantia | None:
        ...
