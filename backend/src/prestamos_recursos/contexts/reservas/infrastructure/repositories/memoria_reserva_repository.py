from copy import deepcopy
from uuid import UUID

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.contexts.reservas.domain.repositories.reserva_repository import (
    ReservaRepository,
)


class MemoriaReservaRepository(ReservaRepository):
    """Almacenamiento temporal: los datos se pierden al reiniciar el proceso."""

    def __init__(self) -> None:
        self._reservas: dict[UUID, Reserva] = {}

    def guardar(self, reserva: Reserva) -> None:
        self._reservas[reserva.id] = deepcopy(reserva)

    def obtener_por_id(self, id: UUID) -> Reserva | None:
        return deepcopy(self._reservas.get(id))

    def obtener_por_usuario(self, id_usuario: UUID) -> list[Reserva]:
        return [
            deepcopy(reserva)
            for reserva in self._reservas.values()
            if reserva.usuario_id == id_usuario
        ]

    def obtener_cola_por_recurso(self, id_recurso: UUID) -> list[Reserva]:
        return [
            deepcopy(reserva)
            for reserva in self._reservas.values()
            if reserva.recurso_id == id_recurso and reserva.estado == EstadoReserva.PENDIENTE
        ]
