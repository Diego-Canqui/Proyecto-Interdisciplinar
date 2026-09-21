from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class ExcepcionAcademica(BaseEntity):
    """«Aggregate Root» ExcepcionAcademica."""

    usuario_id: UUID
    motivo: str
    fecha_inicio: datetime
    fecha_fin: datetime
    activa: bool

    def aprobar(self) -> None:
        raise NotImplementedError

    def rechazar(self) -> None:
        raise NotImplementedError

    def esta_vigente(self) -> bool:
        raise NotImplementedError
