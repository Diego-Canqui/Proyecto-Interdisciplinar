from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.domain.entities.checklist import Checklist
from prestamos_recursos.contexts.prestamos.domain.repositories.checklist_repository import ChecklistRepository


class SqlChecklistRepository(ChecklistRepository):
    """Implementación SQL (SQLAlchemy) de ChecklistRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, checklist: Checklist) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> Checklist | None:
        raise NotImplementedError
