from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.prestamos.domain.entities.checklist import Checklist
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist


class ChecklistRepository(ABC):
    """«Repository» ChecklistRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, checklist: Checklist) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> Checklist | None:
        ...

    @abstractmethod
    def obtener_por_prestamo_y_tipo(
        self, prestamo_id: UUID, tipo: TipoChecklist
    ) -> Checklist | None:
        ...
