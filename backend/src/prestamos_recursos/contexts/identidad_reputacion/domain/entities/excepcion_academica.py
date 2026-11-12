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

    def __post_init__(self) -> None:
        """Valida que la fecha de fin no sea anterior a la de inicio (RF-06)."""
        inicio = self.fecha_inicio
        fin = self.fecha_fin

        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=UTC)
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=UTC)

        if fin < inicio:
            raise ValueError(
                "La fecha de fin de la excepción académica no puede ser anterior a la fecha de inicio"
            )

    def anular(self) -> None:
        """Marca la excepción como anulada (activa=False), p. ej. si se registró por error (RF-22)."""
        self.activa = False

    def es_vigente(self, ahora: datetime | None = None) -> bool:
        """
        Retorna True si la excepción está vigente:
        - activa == True
        - fecha_inicio <= ahora <= fecha_fin (INCLUSIVA, a diferencia de la
          vigencia estricta de las sanciones — RF-14)
        """
        if not self.activa:
            return False

        if ahora is None:
            ahora = datetime.now(UTC)
        elif ahora.tzinfo is None:
            # Normalizar ahora naive a UTC para comparación (manejar naive y aware)
            ahora = ahora.replace(tzinfo=UTC)

        # Normalizar fechas a UTC para comparación (manejar naive y aware)
        inicio = self.fecha_inicio
        fin = self.fecha_fin

        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=UTC)
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=UTC)

        return inicio <= ahora <= fin