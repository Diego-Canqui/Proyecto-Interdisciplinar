from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.reservas.application.dto.reserva_dto import ReservaDTO
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.contexts.reservas.domain.repositories.reserva_repository import ReservaRepository


class ReservaService:
    """«Service» ReservaService."""

    def __init__(self, reserva_repository: ReservaRepository, prestamo_service: PrestamoService) -> None:
        self._reserva_repository = reserva_repository
        self._prestamo_service = prestamo_service

    def crear_reserva(self, id_usuario: UUID, id_recurso: UUID) -> bool:
        raise NotImplementedError

    def cancelar_reserva(self, id_reserva: UUID) -> bool:
        raise NotImplementedError

    def convertir_a_prestamo(self, id_reserva: UUID) -> bool:
        reserva = self._reserva_repository.obtener_por_id(id_reserva)
        if reserva is None or reserva.estado != EstadoReserva.CONFIRMADA:
            return False

        creado = self._prestamo_service.crear_desde_reserva(
            id_reserva=reserva.id,
            id_usuario=reserva.usuario_id,
            id_recurso=reserva.recurso_id,
            fecha_inicio=reserva.fecha_inicio,
            fecha_fin=reserva.fecha_fin,
        )
        if not creado:
            return False

        reserva.convertir_a_prestamo()
        self._reserva_repository.guardar(reserva)
        return True

    def obtener_cola_espera(self, id_recurso: UUID) -> list[ReservaDTO]:
        raise NotImplementedError
