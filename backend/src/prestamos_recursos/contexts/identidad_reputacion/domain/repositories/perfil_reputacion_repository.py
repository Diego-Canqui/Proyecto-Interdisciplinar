from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion


class PerfilReputacionRepository(ABC):
    """«Repository» PerfilReputacionRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, perfil_reputacion: PerfilReputacion) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> PerfilReputacion | None:
        ...
