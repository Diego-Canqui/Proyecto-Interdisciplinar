from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.contexts.reservas.domain.repositories.reserva_repository import (
    ReservaRepository,
)
from prestamos_recursos.contexts.reservas.infrastructure.models.reserva_model import (
    ReservaModel,
)


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

    def obtener_activas_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        consulta = select(ReservaModel).where(
            ReservaModel.recurso_id == id_recurso,
            ReservaModel.estado.in_([EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA]),
        )
        modelos = self._session.scalars(consulta).all()
        return [
            Reserva(
                id=modelo.id,
                usuario_id=modelo.usuario_id,
                recurso_id=modelo.recurso_id,
                fecha_inicio=modelo.fecha_inicio,
                fecha_fin=modelo.fecha_fin,
                estado=modelo.estado,
            )
            for modelo in modelos
        ]

    def obtener_cola_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        raise NotImplementedError
