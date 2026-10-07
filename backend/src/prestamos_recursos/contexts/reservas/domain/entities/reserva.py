from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.shared.base_entity import BaseEntity

_ESTADOS_QUE_OCUPAN_RECURSO = {EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA}


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

    def se_superpone_con(self, otra: Reserva) -> bool:
        """Indica si dos reservas activas ocupan el mismo recurso al mismo tiempo.

        Los horarios que no especifican zona se interpretan como UTC. Si una
        reserva termina justo cuando empieza la otra, no se considera cruce.
        """
        if self.recurso_id != otra.recurso_id:
            return False
        if (
            self.estado not in _ESTADOS_QUE_OCUPAN_RECURSO
            or otra.estado not in _ESTADOS_QUE_OCUPAN_RECURSO
        ):
            return False

        inicio = self._a_utc(self.fecha_inicio)
        fin = self._a_utc(self.fecha_fin)
        otro_inicio = self._a_utc(otra.fecha_inicio)
        otro_fin = self._a_utc(otra.fecha_fin)
        return inicio < otro_fin and otro_inicio < fin

    @staticmethod
    def _a_utc(fecha: datetime) -> datetime:
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha.astimezone(timezone.utc)
