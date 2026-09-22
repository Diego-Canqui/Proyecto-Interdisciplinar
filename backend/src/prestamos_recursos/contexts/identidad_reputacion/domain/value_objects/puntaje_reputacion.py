from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PuntajeReputacion:
    """«Value Object» PuntajeReputacion. Inmutable: los métodos devuelven un objeto nuevo."""

    puntos: int

    def sumar(self, p: int) -> PuntajeReputacion:
        return PuntajeReputacion(puntos=self.puntos + p)

    def restar(self, p: int) -> PuntajeReputacion:
        return PuntajeReputacion(puntos=max(0, self.puntos - p))

    def es_valido(self) -> bool:
        return self.puntos >= 0
