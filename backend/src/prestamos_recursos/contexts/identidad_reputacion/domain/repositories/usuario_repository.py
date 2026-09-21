from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario


class UsuarioRepository(ABC):
    """«Repository» UsuarioRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, usuario: Usuario) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> Usuario | None:
        ...

    @abstractmethod
    def obtener_por_correo(self, correo: str) -> Usuario | None:
        ...

    @abstractmethod
    def listar(self) -> list[Usuario]:
        ...
