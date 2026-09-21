from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.domain.entities.garantia import Garantia
from prestamos_recursos.contexts.prestamos.domain.repositories.garantia_repository import GarantiaRepository


class SqlGarantiaRepository(GarantiaRepository):
    """Implementación SQL (SQLAlchemy) de GarantiaRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, garantia: Garantia) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> Garantia | None:
        raise NotImplementedError
