from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.repositories.reserva_repository import ReservaRepository


class SqlReservaRepository(ReservaRepository):
    """Implementación SQL (SQLAlchemy) de ReservaRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, reserva: Reserva) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> Reserva | None:
        raise NotImplementedError

    def obtener_por_usuario(self, id_usuario: UUID) -> list[Reserva]:
        raise NotImplementedError

    def obtener_cola_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        raise NotImplementedError
