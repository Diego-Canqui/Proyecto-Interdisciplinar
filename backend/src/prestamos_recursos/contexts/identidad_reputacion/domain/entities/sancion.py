from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion


@dataclass(kw_only=True)
class Sancion:
    """Entity Sancion (dentro del agregado PerfilReputacion, no Aggregate Root)."""

    id: UUID = field(default_factory=uuid4)
    tipo: TipoSancion
    puntos_descuento: int
    monto_descuento: Decimal
    motivo: str
    fecha_aplicacion: datetime = field(default_factory=datetime.now)
    activa: bool = False

    def aplicar(self) -> None:
        """Marca la sanción como activa y aplica los descuentos al perfil."""
        self.activa = True

    def calcular_descuento(self) -> int:
        """Retorna los puntos de descuento de la sanción."""
        return self.puntos_descuento

    def generar_cobro(self) -> bool:
        """Retorna True si la sanción genera un cobro (monto_descuento > 0)."""
        return self.monto_descuento > 0