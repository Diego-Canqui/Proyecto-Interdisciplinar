from __future__ import annotations

from datetime import datetime, timedelta, timezone

from prestamos_recursos.contexts.reservas.domain.entities.reserva import Reserva


class AlgoritmoPrioridadService:
    """Prioridad provisional: primero la reserva con fecha de inicio más cercana.

    Las fechas sin zona se interpretan como UTC para comparar criterios iguales.
    En empates se conserva el orden recibido del repositorio.
    """

    def ordenar_cola_espera(self, reservas: list[Reserva]) -> list[Reserva]:
        return sorted(reservas, key=self.calcular_prioridad)

    def calcular_prioridad(self, reserva: Reserva) -> int:
        """Un valor menor tiene prioridad; conserva la precisión de microsegundos."""
        inicio = reserva.fecha_inicio
        if inicio.utcoffset() is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        diferencia = inicio - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return diferencia // timedelta(microseconds=1)
