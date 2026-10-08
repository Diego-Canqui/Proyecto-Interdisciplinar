from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class ExcepcionAcademica(BaseEntity):
    """«Aggregate Root» ExcepcionAcademica."""

    usuario_id: UUID
    motivo: str
    fecha_inicio: datetime
    fecha_fin: datetime
    activa: bool = True

    def aprobar(self) -> None:
        """Marca la excepción como aprobada (activa=True)."""
        self.activa = True

    def rechazar(self) -> None:
        """Marca la excepción como rechazada (activa=False)."""
        self.activa = False

    def es_vigente(self) -> bool:
        """
        Retorna True si la excepción está vigente:
        - activa == True
        - fecha_inicio <= now <= fecha_fin
        """
        if not self.activa:
            return False

        ahora = datetime.now(UTC)
        # Normalizar fechas a UTC para comparación (manejar naive y aware)
        inicio = self.fecha_inicio
        fin = self.fecha_fin

        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=UTC)
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=UTC)

        return inicio <= ahora <= fin