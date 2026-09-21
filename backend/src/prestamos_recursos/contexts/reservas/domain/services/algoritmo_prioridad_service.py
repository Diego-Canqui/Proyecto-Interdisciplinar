from __future__ import annotations

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva


class AlgoritmoPrioridadService:
    """«Domain Service» AlgoritmoPrioridadService."""

    def ordenar_cola_espera(self, reservas: list[Reserva]) -> list[Reserva]:
        raise NotImplementedError

    def calcular_prioridad(self, reserva: Reserva) -> int:
        raise NotImplementedError
