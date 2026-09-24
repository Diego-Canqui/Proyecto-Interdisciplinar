from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Reserva(BaseEntity):
    """«Aggregate Root» Reserva."""

    usuario_id: UUID
    recurso_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoReserva = EstadoReserva.PENDIENTE

    def __post_init__(self) -> None:
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("la fecha de fin debe ser posterior a la fecha de inicio")

    @classmethod
    def crear(
        cls,
        usuario_id: UUID,
        recurso_id: UUID,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> Reserva:
        return cls(
            usuario_id=usuario_id,
            recurso_id=recurso_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    def cancelar(self) -> None:
        if self.estado in {
            EstadoReserva.CANCELADA,
            EstadoReserva.VENCIDA,
            EstadoReserva.CONVERTIDA,
        }:
            raise ValueError("la reserva no se puede cancelar en su estado actual")
        self.estado = EstadoReserva.CANCELADA

    def convertir_a_prestamo(self) -> None:
        if self.estado != EstadoReserva.CONFIRMADA:
            raise ValueError("solo una reserva confirmada puede convertirse en préstamo")
        self.estado = EstadoReserva.CONVERTIDA

    def esta_vigente(self, fecha_actual: datetime | None = None) -> bool:
        fecha_actual = fecha_actual or datetime.now(tz=self.fecha_fin.tzinfo)
        return (
            self.estado in {EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA}
            and self.fecha_fin >= fecha_actual
        )
