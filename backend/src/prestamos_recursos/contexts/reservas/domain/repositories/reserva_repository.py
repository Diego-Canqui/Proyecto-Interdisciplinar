from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva


class ReservaRepository(ABC):
    """«Repository» ReservaRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, reserva: Reserva) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> Reserva | None:
        ...

    @abstractmethod
    def obtener_por_usuario(self, id_usuario: UUID) -> list[Reserva]:
        ...

    @abstractmethod
    def obtener_cola_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        ...
