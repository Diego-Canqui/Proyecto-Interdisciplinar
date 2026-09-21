from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.reservas.application.dto.reserva_dto import ReservaDTO
from prestamos_recursos.contexts.reservas.domain.repositories.reserva_repository import ReservaRepository


class ReservaService:
    """«Service» ReservaService."""

    def __init__(self, reserva_repository: ReservaRepository) -> None:
        self._reserva_repository = reserva_repository

    def crear_reserva(self, id_usuario: UUID, id_recurso: UUID) -> bool:
        raise NotImplementedError

    def cancelar_reserva(self, id_reserva: UUID) -> bool:
        raise NotImplementedError

    def convertir_a_prestamo(self, id_reserva: UUID) -> bool:
        raise NotImplementedError

    def obtener_cola_espera(self, id_recurso: UUID) -> list[ReservaDTO]:
        raise NotImplementedError
