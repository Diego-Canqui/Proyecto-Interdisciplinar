from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.domain.value_objects.compromiso_responsabilidad import (
    CompromisoResponsabilidad,
)
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Garantia(BaseEntity):
    """«Aggregate Root» Garantia."""

    prestamo_id: UUID
    tipo: TipoGarantia
    estado: EstadoGarantia
    fecha_registro: datetime
    fecha_liberacion: datetime | None = None
    compromiso: CompromisoResponsabilidad

    def registrar(self) -> None:
        if self.estado != EstadoGarantia.PENDIENTE:
            raise ValueError("Sólo se puede registrar una garantía pendiente")
        if not self.compromiso.contenido.strip() or not self.compromiso.firma_url.strip():
            raise ValueError("El compromiso de responsabilidad no es válido")
        self.estado = EstadoGarantia.REGISTRADA

    def liberar(self, fecha_liberacion: datetime | None = None) -> None:
        """Libera la garantía tras devolución conforme (RF-05)."""
        if self.estado not in {EstadoGarantia.REGISTRADA, EstadoGarantia.PENDIENTE}:
            raise ValueError("Sólo se puede liberar una garantía registrada o pendiente")
        self.estado = EstadoGarantia.LIBERADA
        self.fecha_liberacion = fecha_liberacion or datetime.now(UTC)

    def retener(self) -> None:
        """Retiene la garantía ante daños detectados en la devolución (RF-05)."""
        if self.estado not in {EstadoGarantia.REGISTRADA, EstadoGarantia.PENDIENTE}:
            raise ValueError("Sólo se puede retener una garantía registrada o pendiente")
        self.estado = EstadoGarantia.RETENIDA
        self.fecha_liberacion = None
