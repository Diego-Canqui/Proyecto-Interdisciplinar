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

    def agregar_item(self, observaciones: str, fotos_urls: list[str]) -> None:
        if self.completo:
            raise ValueError("No se pueden modificar checklists confirmados")
        texto = observaciones.strip()
        if not texto and not fotos_urls:
            raise ValueError("El ítem debe incluir observaciones o al menos una foto")
        if texto:
            self.observaciones = f"{self.observaciones}\n{texto}".strip()
        self.fotos_urls.extend(fotos_urls)

    def confirmar(self) -> None:
        if self.completo:
            raise ValueError("El checklist ya está confirmado")
        if not self.observaciones.strip() and not self.fotos_urls:
            raise ValueError("El checklist debe incluir al menos un ítem")
        self.completo = True

    def crear_inicial(self) -> None:
        raise NotImplementedError

    def crear_devolucion(self) -> None:
        raise NotImplementedError

    def comparar_estado(self) -> None:
        raise NotImplementedError
