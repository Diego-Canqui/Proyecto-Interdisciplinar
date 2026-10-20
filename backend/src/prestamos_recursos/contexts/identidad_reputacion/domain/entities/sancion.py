from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    fecha_fin: datetime
    activa: bool = False

    def aplicar(self) -> None:
        """Marca la sanción como activa y aplica los descuentos al perfil."""
        self.activa = True

    def calcular_descuento(self) -> int:
        """Retorna los puntos de descuento de la sanción."""
        return self.puntos_descuento

    def esta_vigente(self, ahora: datetime | None = None) -> bool:
        """
        Retorna True si la sanción está vigente (bloquea la elegibilidad):
        - activa == True
        - fecha_fin > ahora (ESTRICTA: en su fecha de fin ya expiró)

        Normaliza fechas naive a UTC para la comparación, como hace
        ExcepcionAcademica.es_vigente.
        """
        if not self.activa:
            return False

        if ahora is None:
            ahora = datetime.now(UTC)
        elif ahora.tzinfo is None:
            # Normalizar ahora naive a UTC para comparación (manejar naive y aware)
            ahora = ahora.replace(tzinfo=UTC)

        # Normalizar fecha_fin a UTC para comparación (manejar naive y aware)
        fin = self.fecha_fin
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=UTC)

        return fin > ahora