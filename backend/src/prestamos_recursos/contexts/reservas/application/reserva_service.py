from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.reservas.application.dto.reserva_dto import (
    CrearReservaDTO,
    ReservaDTO,
)
from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.repositories.reserva_repository import (
    ReservaRepository,
)
from prestamos_recursos.contexts.reservas.domain.services.algoritmo_prioridad_service import (
    AlgoritmoPrioridadService,
)


class ReservaService:
    """«Service» ReservaService."""

    def __init__(self, reserva_repository: ReservaRepository) -> None:
        self._reserva_repository = reserva_repository
        self._prioridad_service = AlgoritmoPrioridadService()

    def crear_reserva(self, datos: CrearReservaDTO) -> ReservaDTO:
        reserva = Reserva.crear(**datos.model_dump())
        self._reserva_repository.guardar(reserva)
        return ReservaDTO.model_validate(reserva)

    def obtener_reserva(self, id_reserva: UUID) -> ReservaDTO:
        return ReservaDTO.model_validate(self._buscar_reserva(id_reserva))

    def cancelar_reserva(self, id_reserva: UUID) -> bool:
        reserva = self._buscar_reserva(id_reserva)
        reserva.cancelar()
        self._reserva_repository.guardar(reserva)
        return True

    def convertir_a_prestamo(self, id_reserva: UUID) -> bool:
        raise NotImplementedError("pendiente de integrar con el módulo de préstamos")

    def obtener_cola_espera(self, id_recurso: UUID) -> list[ReservaDTO]:
        reservas = self._reserva_repository.obtener_cola_por_recurso(id_recurso)
        vigentes = [reserva for reserva in reservas if reserva.esta_vigente()]
        ordenadas = self._prioridad_service.ordenar_cola_espera(vigentes)
        return [ReservaDTO.model_validate(reserva) for reserva in ordenadas]

    def _buscar_reserva(self, id_reserva: UUID) -> Reserva:
        reserva = self._reserva_repository.obtener_por_id(id_reserva)
        if reserva is None:
            raise LookupError("reserva no encontrada")
        return reserva
