from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Checklist(BaseEntity):
    """«Aggregate Root» Checklist."""

    prestamo_id: UUID
    tipo: TipoChecklist
    fecha_inspeccion: datetime
    observaciones: str
    fotos_urls: list[str] = field(default_factory=list)
    completo: bool

    def crear_inicial(self) -> None:
        raise NotImplementedError

    def crear_devolucion(self) -> None:
        raise NotImplementedError

    def comparar_estado(self) -> None:
        raise NotImplementedError
