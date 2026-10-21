from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.reservas.application.dto.reserva_dto import (
    CrearReservaDTO,
    ReservaDTO,
)
from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva
from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.contexts.reservas.domain.repositories.reserva_repository import (
    ReservaRepository,
)
from prestamos_recursos.contexts.reservas.domain.services.algoritmo_prioridad_service import (
    AlgoritmoPrioridadService,
)


class ReservaService:
    """«Service» ReservaService."""

    def __init__(
        self,
        reserva_repository: ReservaRepository,
        prestamo_service: PrestamoService,
    ) -> None:
        self._reserva_repository = reserva_repository
        self._prioridad_service = AlgoritmoPrioridadService()
        self._prestamo_service = prestamo_service

    def crear_reserva(self, datos: CrearReservaDTO) -> ReservaDTO:
        reserva = Reserva.crear(**datos.model_dump())
        reservas_activas = self._reserva_repository.obtener_activas_por_recurso(
            reserva.recurso_id
        )
        if any(reserva.se_superpone_con(otra) for otra in reservas_activas):
            raise ValueError("el recurso ya tiene una reserva activa en ese horario")

        self._reserva_repository.guardar(reserva)
        return ReservaDTO.model_validate(reserva)

    def obtener_reserva(self, id_reserva: UUID) -> ReservaDTO:
        return ReservaDTO.model_validate(self._buscar_reserva(id_reserva))

    def obtener_por_usuario(self, id_usuario: UUID) -> list[ReservaDTO]:
        reservas = self._reserva_repository.obtener_por_usuario(id_usuario)
        return [ReservaDTO.model_validate(reserva) for reserva in reservas]

    def confirmar_reserva(self, id_reserva: UUID) -> ReservaDTO:
        reserva = self._buscar_reserva(id_reserva)
        reservas_activas = self._reserva_repository.obtener_activas_por_recurso(
            reserva.recurso_id
        )
        if any(
            otra.id != reserva.id and reserva.se_superpone_con(otra)
            for otra in reservas_activas
        ):
            raise ValueError("el recurso ya tiene una reserva activa en ese horario")

        reserva.confirmar()
        self._reserva_repository.guardar(reserva)
        return ReservaDTO.model_validate(reserva)

    def cancelar_reserva(self, id_reserva: UUID) -> bool:
        reserva = self._buscar_reserva(id_reserva)
        reserva.cancelar()
        self._reserva_repository.guardar(reserva)
        return True

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
        reservas = self._reserva_repository.obtener_cola_por_recurso(id_recurso)
        vigentes = [reserva for reserva in reservas if reserva.esta_vigente()]
        ordenadas = self._prioridad_service.ordenar_cola_espera(vigentes)
        return [ReservaDTO.model_validate(reserva) for reserva in ordenadas]

    def _buscar_reserva(self, id_reserva: UUID) -> Reserva:
        reserva = self._reserva_repository.obtener_por_id(id_reserva)
        if reserva is None:
            raise LookupError("reserva no encontrada")
        return reserva
