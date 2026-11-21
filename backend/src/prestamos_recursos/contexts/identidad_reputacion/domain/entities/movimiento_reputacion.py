from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_movimiento_reputacion import (
    TipoMovimientoReputacion,
)


@dataclass(frozen=True, kw_only=True)
class MovimientoReputacion:
    """Registro histórico inmutable de una variación o evento sobre el puntaje."""

    usuario_id: UUID
    tipo: TipoMovimientoReputacion
    motivo: str
    puntaje_anterior: int
    variacion_puntos: int
    puntaje_resultante: int
    id: UUID = field(default_factory=uuid4)
    fecha_movimiento: datetime = field(default_factory=lambda: datetime.now(UTC))
    numero_secuencia: int = 1
    sancion_id: UUID | None = None
    prestamo_id: UUID | None = None
    reserva_id: UUID | None = None
    recurso_id: UUID | None = None
    recurso_nombre: str | None = None

    def __post_init__(self) -> None:
        if not (0 <= self.puntaje_anterior <= 1000) or not (0 <= self.puntaje_resultante <= 1000):
            raise ValueError("El puntaje anterior y resultante debe estar entre 0 y 1000")
        if self.variacion_puntos != self.puntaje_resultante - self.puntaje_anterior:
            raise ValueError(
                "La variacion_puntos debe coincidir exactamente con "
                "puntaje_resultante - puntaje_anterior"
            )
        if not self.motivo or not self.motivo.strip():
            raise ValueError("El motivo del movimiento no puede estar vacío")
        if self.numero_secuencia < 1:
            raise ValueError("El numero_secuencia debe ser mayor o igual a 1")
