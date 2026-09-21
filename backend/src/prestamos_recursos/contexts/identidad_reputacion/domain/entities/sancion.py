from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Sancion(BaseEntity):
    """«Aggregate Root» Sancion."""

    perfil_reputacion_id: UUID
    tipo: TipoSancion
    puntos_descuento: int
    monto_descuento: Decimal
    motivo: str
    fecha_aplicacion: datetime
    activa: bool

    def aplicar(self) -> None:
        raise NotImplementedError

    def calcular_descuento(self) -> int:
        raise NotImplementedError

    def generar_cobro(self) -> bool:
        raise NotImplementedError
