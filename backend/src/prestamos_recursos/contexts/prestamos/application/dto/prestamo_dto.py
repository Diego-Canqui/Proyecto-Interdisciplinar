from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo


class PrestamoDTO(BaseModel):
    """DTO PrestamoDTO."""

    id: UUID
    reserva_id: UUID
    recurso_id: UUID
    usuario_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoPrestamo

    @classmethod
    def from_entity(cls, prestamo: Prestamo) -> PrestamoDTO:
        """Crea un PrestamoDTO desde una entidad Prestamo del dominio."""
        return cls(
            id=prestamo.id,
            reserva_id=prestamo.reserva_id,
            recurso_id=prestamo.recurso_id,
            usuario_id=prestamo.usuario_id,
            fecha_inicio=prestamo.fecha_inicio,
            fecha_fin=prestamo.fecha_fin,
            estado=prestamo.estado,
        )

    model_config = {"from_attributes": True}

