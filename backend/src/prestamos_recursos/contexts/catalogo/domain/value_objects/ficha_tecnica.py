from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FichaTecnica:
    """«Value Object» FichaTecnica. Inmutable: los métodos devuelven un objeto nuevo."""

    marca: str
    modelo: str
    numero_serie: str
    color: str
    estado_fisico: str
    foto_url: str

    def es_valida(self) -> bool:
        """Verifica si la ficha técnica es válida asegurando que los campos esenciales no estén vacíos."""
        return bool(
            self.marca.strip()
            and self.modelo.strip()
            and self.numero_serie.strip()
            and self.estado_fisico.strip()
        )
