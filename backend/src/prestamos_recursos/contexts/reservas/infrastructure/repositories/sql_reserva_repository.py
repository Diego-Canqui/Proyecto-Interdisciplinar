from __future__ import annotations

from datetime import UTC, datetime
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
        modelo = ReservaModel(
            id=reserva.id,
            usuario_id=reserva.usuario_id,
            recurso_id=reserva.recurso_id,
            fecha_inicio=reserva.fecha_inicio,
            fecha_fin=reserva.fecha_fin,
            estado=reserva.estado,
        )
        try:
            self._session.merge(modelo)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def obtener_por_id(self, id: UUID) -> Reserva | None:
        modelo = self._session.get(ReservaModel, id)
        return self._a_entidad(modelo) if modelo is not None else None

    def obtener_por_usuario(self, id_usuario: UUID) -> list[Reserva]:
        consulta = (
            select(ReservaModel)
            .where(ReservaModel.usuario_id == id_usuario)
            .order_by(ReservaModel.fecha_inicio, ReservaModel.id)
        )
        return [self._a_entidad(modelo) for modelo in self._session.scalars(consulta)]

    def obtener_activas_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        consulta = select(ReservaModel).where(
            ReservaModel.recurso_id == id_recurso,
            ReservaModel.estado.in_([EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA]),
        )
        modelos = self._session.scalars(consulta).all()
        return [self._a_entidad(modelo) for modelo in modelos]

    def obtener_cola_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        consulta = (
            select(ReservaModel)
            .where(
                ReservaModel.recurso_id == id_recurso,
                ReservaModel.estado == EstadoReserva.PENDIENTE,
            )
            .order_by(ReservaModel.fecha_inicio, ReservaModel.id)
        )
        return [self._a_entidad(modelo) for modelo in self._session.scalars(consulta)]

    @staticmethod
    def _a_entidad(modelo: ReservaModel) -> Reserva:
        return Reserva(
            id=modelo.id,
            usuario_id=modelo.usuario_id,
            recurso_id=modelo.recurso_id,
            fecha_inicio=SqlReservaRepository._a_utc(modelo.fecha_inicio),
            fecha_fin=SqlReservaRepository._a_utc(modelo.fecha_fin),
            estado=modelo.estado,
        )

    @staticmethod
    def _a_utc(fecha: datetime) -> datetime:
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=UTC)
        return fecha.astimezone(UTC)
