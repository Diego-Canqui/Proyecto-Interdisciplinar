from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.contexts.reservas.domain.repositories.reserva_repository import (
    ReservaRepository,
)
from prestamos_recursos.contexts.reservas.infrastructure.models.reserva_model import ReservaModel


class SqlReservaRepository(ReservaRepository):
    """Implementación SQL (SQLAlchemy) de ReservaRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, reserva: Reserva) -> None:
        modelo = self._session.get(ReservaModel, reserva.id)
        if modelo is None:
            modelo = ReservaModel(id=reserva.id)
            self._session.add(modelo)

        modelo.usuario_id = reserva.usuario_id
        modelo.recurso_id = reserva.recurso_id
        modelo.fecha_inicio = reserva.fecha_inicio
        modelo.fecha_fin = reserva.fecha_fin
        modelo.estado = reserva.estado

    def obtener_por_id(self, id: UUID) -> Reserva | None:
        modelo = self._session.get(ReservaModel, id)
        if modelo is None:
            return None

        return Reserva(
            id=modelo.id,
            usuario_id=modelo.usuario_id,
            recurso_id=modelo.recurso_id,
            fecha_inicio=modelo.fecha_inicio,
            fecha_fin=modelo.fecha_fin,
            estado=EstadoReserva(modelo.estado),
        )

    def obtener_por_usuario(self, id_usuario: UUID) -> list[Reserva]:
        raise NotImplementedError

    def obtener_cola_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        raise NotImplementedError
