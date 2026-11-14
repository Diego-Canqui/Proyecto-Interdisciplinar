from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _normalizar_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio if limpio else None


@dataclass(frozen=True)
class FichaTecnica:
    """«Value Object» FichaTecnica. Inmutable: los métodos devuelven un objeto nuevo."""

    estado_fisico: str
    foto_url: str
    marca: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    color: str | None = None
    especificaciones: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for campo in ("marca", "modelo", "numero_serie", "color"):
            object.__setattr__(self, campo, _normalizar_opcional(getattr(self, campo)))
        if self.especificaciones is None:
            object.__setattr__(self, "especificaciones", {})

    def es_valida(self) -> bool:
        """Verifica si la ficha técnica es válida asegurando estado físico y especificaciones."""
        return bool(
            self.estado_fisico.strip()
            and isinstance(self.especificaciones, dict)
        )
