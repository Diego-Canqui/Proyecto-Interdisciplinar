from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.movimiento_reputacion import (
    MovimientoReputacion,
)


class MovimientoReputacionRepository(ABC):
    """Repositorio append-only de la bitácora inmutable de reputación."""

    @abstractmethod
    def registrar(self, movimiento: MovimientoReputacion) -> None:
        """Registra un nuevo movimiento sin permitir ediciones ni borrados."""
        ...

    @abstractmethod
    def obtener_por_usuario(self, usuario_id: UUID) -> list[MovimientoReputacion]:
        """Retorna los movimientos de un usuario ordenados del más reciente al más antiguo."""
        ...

    @abstractmethod
    def obtener_todos(self) -> list[MovimientoReputacion]:
        """Retorna todos los movimientos del sistema ordenados cronológicamente."""
        ...

    @abstractmethod
    def contar_por_usuario(self, usuario_id: UUID) -> int:
        """Retorna la cantidad de movimientos persistidos de un usuario."""
        ...

    @abstractmethod
    def obtener_siguiente_secuencia(self, usuario_id: UUID) -> int:
        """Calcula el siguiente número de secuencia determinista para el usuario."""
        ...
