from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva


class AlgoritmoPrioridadService:
    """Prioridad: primero mayor reputación (descendente) y menor fecha de inicio (en microsegundos).

    Las fechas sin zona se interpretan como UTC para comparar criterios iguales.
    En empates se conserva el orden recibido del repositorio.
    """

    def ordenar_cola_espera(
        self,
        reservas: list[Reserva],
        puntajes_por_usuario: dict[UUID, int] | None = None,
    ) -> list[Reserva]:
        puntajes = puntajes_por_usuario or {}
        return sorted(
            reservas,
            key=lambda reserva: self.calcular_prioridad(
                reserva,
                puntajes.get(reserva.usuario_id, 500),
            ),
        )

    def calcular_prioridad(self, reserva: Reserva, puntaje: int = 500) -> tuple[int, int]:
        """Retorna (-puntaje, diferencia_microsegundos); menor valor tiene mayor prioridad."""
        inicio = reserva.fecha_inicio
        if inicio.utcoffset() is None:
            inicio = inicio.replace(tzinfo=UTC)
        diferencia = inicio - datetime(1970, 1, 1, tzinfo=UTC)
        diferencia_microsegundos = diferencia // timedelta(microseconds=1)
        return (-puntaje, diferencia_microsegundos)

