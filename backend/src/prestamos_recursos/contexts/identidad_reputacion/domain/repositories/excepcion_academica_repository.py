from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)


class ExcepcionAcademicaRepository(ABC):
    """«Repository» ExcepcionAcademicaRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, excepcion_academica: ExcepcionAcademica) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> ExcepcionAcademica | None:
        ...

    @abstractmethod
    def obtener_vigentes_por_usuario(self, usuario_id: UUID) -> list[ExcepcionAcademica]:
        ...

    @abstractmethod
    def obtener_por_usuario(self, usuario_id: UUID) -> list[ExcepcionAcademica]:
        """Todas las excepciones del usuario (activas, anuladas, vencidas y programadas),
        ordenadas por fecha de inicio descendente. No filtra por vigencia.

        Es una consulta de solo lectura: no crea ni modifica datos (RF-04).
        """
        ...
