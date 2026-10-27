from __future__ import annotations

from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from prestamos_recursos.contexts.identidad_reputacion.application.reputacion_service import (
        ReputacionService,
    )


class ReservaService:
    """«Service» ReservaService."""

    def __init__(
        self,
        reserva_repository: ReservaRepository,
        prestamo_service: PrestamoService,
        reputacion_service: ReputacionService | None = None,
    ) -> None:
        self._reserva_repository = reserva_repository
        self._prioridad_service = AlgoritmoPrioridadService()
        self._prestamo_service = prestamo_service
        self._reputacion_service = reputacion_service

    def _obtener_puntaje_usuario(self, usuario_id: UUID) -> int:
        if self._reputacion_service is None:
            return 500
        try:
            perfil = self._reputacion_service.obtener_perfil(usuario_id)
            return perfil.puntaje
        except Exception:  # noqa: BLE001
            return 500

    def crear_reserva(self, datos: CrearReservaDTO) -> ReservaDTO:
        reserva = Reserva.crear(**datos.model_dump())
        reservas_activas = self._reserva_repository.obtener_activas_por_recurso(
            reserva.recurso_id
        )
        if any(
            otra.usuario_id == reserva.usuario_id and reserva.se_superpone_con(otra)
            for otra in reservas_activas
        ):
            raise ValueError("ya tienes una reserva activa para este recurso en ese horario")

        if any(
            otra.estado == EstadoReserva.CONFIRMADA and reserva.se_superpone_con(otra)
            for otra in reservas_activas
        ):
            self._reserva_repository.guardar(reserva)
            return ReservaDTO.model_validate(reserva)

        reserva.confirmar()
        self._reserva_repository.guardar(reserva)
        return ReservaDTO.model_validate(reserva)

    def obtener_reserva(self, id_reserva: UUID) -> ReservaDTO:
        return ReservaDTO.model_validate(self._buscar_reserva(id_reserva))

    def obtener_por_usuario(self, id_usuario: UUID) -> list[ReservaDTO]:
        reservas = self._reserva_repository.obtener_por_usuario(id_usuario)
        return [ReservaDTO.model_validate(reserva) for reserva in reservas]

    def obtener_todas(self) -> list[ReservaDTO]:
        reservas = self._reserva_repository.obtener_todas()
        return [ReservaDTO.model_validate(reserva) for reserva in reservas]

    def confirmar_reserva(self, id_reserva: UUID) -> ReservaDTO:
        reserva = self._buscar_reserva(id_reserva)
        reservas_activas = self._reserva_repository.obtener_activas_por_recurso(
            reserva.recurso_id
        )
        if any(
            otra.id != reserva.id
            and otra.estado == EstadoReserva.CONFIRMADA
            and reserva.se_superpone_con(otra)
            for otra in reservas_activas
        ):
            raise ValueError("el recurso ya tiene una reserva confirmada en ese horario")

        reserva.confirmar()
        self._reserva_repository.guardar(reserva)
        return ReservaDTO.model_validate(reserva)

    def cancelar_reserva(self, id_reserva: UUID) -> bool:
        reserva = self._buscar_reserva(id_reserva)
        estaba_confirmada = reserva.estado == EstadoReserva.CONFIRMADA
        inicio_liberado = Reserva._a_utc(reserva.fecha_inicio)
        fin_liberado = Reserva._a_utc(reserva.fecha_fin)

        reserva.cancelar()
        self._reserva_repository.guardar(reserva)

        if estaba_confirmada:
            cola = self._reserva_repository.obtener_cola_por_recurso(reserva.recurso_id)
            candidatas = [
                c
                for c in cola
                if c.esta_vigente()
                and Reserva._a_utc(c.fecha_inicio) < fin_liberado
                and inicio_liberado < Reserva._a_utc(c.fecha_fin)
            ]
            if candidatas:
                puntajes = {
                    c.usuario_id: self._obtener_puntaje_usuario(c.usuario_id)
                    for c in candidatas
                }
                ordenadas = self._prioridad_service.ordenar_cola_espera(candidatas, puntajes)
                confirmadas_actuales = [
                    r
                    for r in self._reserva_repository.obtener_activas_por_recurso(reserva.recurso_id)
                    if r.estado == EstadoReserva.CONFIRMADA
                ]
                for candidata in ordenadas:
                    if not any(candidata.se_superpone_con(conf) for conf in confirmadas_actuales):
                        candidata.confirmar()
                        self._reserva_repository.guardar(candidata)
                        break

        return True

    def convertir_a_prestamo(self, id_reserva: UUID) -> bool:
        reserva = self._reserva_repository.obtener_por_id(id_reserva)
        if reserva is None or reserva.estado != EstadoReserva.CONFIRMADA:
            return False

        creado = self._prestamo_service.solicitar_prestamo(
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
        puntajes = {
            reserva.usuario_id: self._obtener_puntaje_usuario(reserva.usuario_id)
            for reserva in vigentes
        }
        ordenadas = self._prioridad_service.ordenar_cola_espera(vigentes, puntajes)
        return [ReservaDTO.model_validate(reserva) for reserva in ordenadas]

    def _buscar_reserva(self, id_reserva: UUID) -> Reserva:
        reserva = self._reserva_repository.obtener_por_id(id_reserva)
        if reserva is None:
            raise LookupError("reserva no encontrada")
        return reserva
