from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PuntajeReputacion:
    """«Value Object» PuntajeReputacion. Inmutable: los métodos devuelven un objeto nuevo."""

    puntos: int

    def sumar(self, p: int) -> PuntajeReputacion:
        raise NotImplementedError

    def restar(self, p: int) -> PuntajeReputacion:
        raise NotImplementedError

    def es_valido(self) -> bool:
        raise NotImplementedError
