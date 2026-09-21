from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.perfil_reputacion_repository import PerfilReputacionRepository


class SqlPerfilReputacionRepository(PerfilReputacionRepository):
    """Implementación SQL (SQLAlchemy) de PerfilReputacionRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, perfil_reputacion: PerfilReputacion) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> PerfilReputacion | None:
        raise NotImplementedError
