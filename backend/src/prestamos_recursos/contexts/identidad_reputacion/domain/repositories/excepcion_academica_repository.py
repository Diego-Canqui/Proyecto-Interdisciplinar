from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica


class ExcepcionAcademicaRepository(ABC):
    """«Repository» ExcepcionAcademicaRepository (interfaz del dominio)."""

    @abstractmethod
    def guardar(self, excepcion_academica: ExcepcionAcademica) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, id: UUID) -> ExcepcionAcademica | None:
        ...
