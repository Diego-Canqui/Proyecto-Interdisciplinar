from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Prestamo(BaseEntity):
    """«Aggregate Root» Prestamo."""

    reserva_id: UUID
    recurso_id: UUID
    usuario_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoPrestamo

    def iniciar(self) -> None:
        raise NotImplementedError

    def devolver(self) -> None:
        raise NotImplementedError

    def renovar(self) -> None:
        raise NotImplementedError

    def vencer(self) -> None:
        raise NotImplementedError

    def solicitar_prorroga(self) -> bool:
        raise NotImplementedError
