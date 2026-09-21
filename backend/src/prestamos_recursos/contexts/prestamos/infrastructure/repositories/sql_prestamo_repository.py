from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.repositories.prestamo_repository import PrestamoRepository


class SqlPrestamoRepository(PrestamoRepository):
    """Implementación SQL (SQLAlchemy) de PrestamoRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, prestamo: Prestamo) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> Prestamo | None:
        raise NotImplementedError

    def obtener_activos(self) -> list[Prestamo]:
        raise NotImplementedError

    def obtener_por_usuario(self, id_usuario: UUID) -> list[Prestamo]:
        raise NotImplementedError
