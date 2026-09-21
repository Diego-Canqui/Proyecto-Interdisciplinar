from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.catalogo.application.dto.recurso_dto import RecursoDTO
from prestamos_recursos.contexts.catalogo.domain.repositories.recurso_repository import RecursoRepository


class RecursoService:
    """«Service» RecursoService."""

    def __init__(self, recurso_repository: RecursoRepository) -> None:
        self._recurso_repository = recurso_repository

    def buscar_recursos(self, filtro: str) -> list[RecursoDTO]:
        raise NotImplementedError

    def consultar_disponibilidad(self, id_recurso: UUID) -> bool:
        raise NotImplementedError

    def obtener_ficha_tecnica(self, id_recurso: UUID) -> RecursoDTO:
        raise NotImplementedError
