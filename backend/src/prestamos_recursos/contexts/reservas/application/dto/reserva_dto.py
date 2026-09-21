from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva


class ReservaDTO(BaseModel):
    """DTO ReservaDTO. TODO: ajustar los campos a lo que necesite el frontend."""

    id: UUID
    usuario_id: UUID
    recurso_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoReserva
