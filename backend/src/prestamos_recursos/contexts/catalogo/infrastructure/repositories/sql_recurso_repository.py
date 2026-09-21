from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.catalogo.domain.entities.recurso import Recurso
from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.catalogo.domain.repositories.recurso_repository import RecursoRepository


class SqlRecursoRepository(RecursoRepository):
    """Implementación SQL (SQLAlchemy) de RecursoRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, recurso: Recurso) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> Recurso | None:
        raise NotImplementedError

    def buscar_disponibles(self, categoria: str) -> list[Recurso]:
        raise NotImplementedError

    def actualizar_estado(self, id_recurso: UUID, estado: EstadoRecurso) -> None:
        raise NotImplementedError
