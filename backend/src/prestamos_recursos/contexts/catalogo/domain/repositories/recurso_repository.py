from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.catalogo.domain.entities.recurso import Recurso
from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso


class RecursoRepository(ABC):
    """«Repository» RecursoRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, recurso: Recurso) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> Recurso | None:
        ...

    @abstractmethod
    def buscar_disponibles(self, categoria: str) -> list[Recurso]:
        ...

    @abstractmethod
    def actualizar_estado(self, id_recurso: UUID, estado: EstadoRecurso) -> None:
        ...
