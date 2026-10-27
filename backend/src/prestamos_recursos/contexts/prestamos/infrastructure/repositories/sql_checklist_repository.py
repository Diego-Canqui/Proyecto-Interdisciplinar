from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.domain.entities.checklist import Checklist
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.contexts.prestamos.domain.repositories.checklist_repository import (
    ChecklistRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.models.checklist_model import (
    ChecklistModel,
)


class SqlChecklistRepository(ChecklistRepository):
    """Implementación SQL (SQLAlchemy) de ChecklistRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, modelo: ChecklistModel) -> Checklist:
        return Checklist(
            id=modelo.id,
            prestamo_id=modelo.prestamo_id,
            tipo=modelo.tipo,
            fecha_inspeccion=modelo.fecha_inspeccion,
            observaciones=modelo.observaciones,
            fotos_urls=modelo.fotos_urls or [],
            completo=modelo.completo,
        )

    def _to_model(self, checklist: Checklist) -> ChecklistModel:
        modelo = self._session.get(ChecklistModel, checklist.id)
        if modelo is None:
            modelo = ChecklistModel(id=checklist.id)
            self._session.add(modelo)
        modelo.prestamo_id = checklist.prestamo_id
        modelo.tipo = checklist.tipo
        modelo.fecha_inspeccion = checklist.fecha_inspeccion
        modelo.observaciones = checklist.observaciones
        modelo.fotos_urls = checklist.fotos_urls
        modelo.completo = checklist.completo
        return modelo

    def guardar(self, checklist: Checklist) -> None:
        """Persistir o actualizar un checklist en la base de datos."""
        self._to_model(checklist)
        # Session commit handled by caller.

    def obtener_por_id(self, id: UUID) -> Checklist | None:
        modelo = self._session.get(ChecklistModel, id)
        if modelo is None:
            return None
        return self._to_entity(modelo)

    def obtener_por_prestamo_y_tipo(
        self, prestamo_id: UUID, tipo: TipoChecklist
    ) -> Checklist | None:
        modelo = self._session.scalar(
            select(ChecklistModel).where(
                ChecklistModel.prestamo_id == prestamo_id,
                ChecklistModel.tipo == tipo,
            )
        )
        return self._to_entity(modelo) if modelo is not None else None
