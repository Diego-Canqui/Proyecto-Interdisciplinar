from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CompromisoResponsabilidad:
    """«Value Object» CompromisoResponsabilidad. Inmutable: los métodos devuelven un objeto nuevo."""

    contenido: str
    fecha_firma: datetime
    firma_url: str
    testigo: str

    def es_valido(self) -> bool:
        raise NotImplementedError
