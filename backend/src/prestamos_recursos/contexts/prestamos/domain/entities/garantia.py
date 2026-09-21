from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.domain.value_objects.compromiso_responsabilidad import CompromisoResponsabilidad
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
        raise NotImplementedError

    def liberar(self) -> None:
        raise NotImplementedError

    def retener(self) -> None:
        raise NotImplementedError
