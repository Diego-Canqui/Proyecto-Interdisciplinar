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
    estado: EstadoReserva

    def crear(self) -> None:
        raise NotImplementedError

    def cancelar(self) -> None:
        raise NotImplementedError

    def convertir_a_prestamo(self) -> None:
        raise NotImplementedError

    def esta_vigente(self) -> bool:
        raise NotImplementedError
