from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.sancion_repository import SancionRepository


class SqlSancionRepository(SancionRepository):
    """Implementación SQL (SQLAlchemy) de SancionRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, sancion: Sancion) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> Sancion | None:
        raise NotImplementedError
