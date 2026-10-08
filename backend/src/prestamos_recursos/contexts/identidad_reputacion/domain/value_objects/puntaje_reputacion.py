from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PuntajeReputacion:
    """«Value Object» PuntajeReputacion. Inmutable: los métodos devuelven un objeto nuevo.

    Rango válido: 0..1000 inclusive.
    """

    puntos: int

    def __post_init__(self) -> None:
        """Validar que puntos esté en rango 0..1000."""
        if not isinstance(self.puntos, int):
            raise TypeError("Los puntos deben ser un entero")
        if self.puntos < 0 or self.puntos > 1000:
            raise ValueError(f"PuntajeReputacion debe estar en rango 0..1000, recibido: {self.puntos}")

    def sumar(self, p: int) -> PuntajeReputacion:
        """Sumar puntos y devolver nueva instancia validada."""
        return PuntajeReputacion(puntos=self.puntos + p)

    def restar(self, p: int) -> PuntajeReputacion:
        """Restar puntos y devolver nueva instancia validada (clamp a 0 mínimo)."""
        nuevo_puntos = max(self.puntos - p, 0)
        return PuntajeReputacion(puntos=nuevo_puntos)

    def es_valido(self) -> bool:
        """Verificar si el puntaje es válido (>= 0)."""
        return self.puntos >= 0