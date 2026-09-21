from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.excepcion_academica_repository import ExcepcionAcademicaRepository


class SqlExcepcionAcademicaRepository(ExcepcionAcademicaRepository):
    """Implementación SQL (SQLAlchemy) de ExcepcionAcademicaRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, excepcion_academica: ExcepcionAcademica) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> ExcepcionAcademica | None:
        raise NotImplementedError
