from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo


class PrestamoDTO(BaseModel):
    """DTO PrestamoDTO. TODO: ajustar los campos a lo que necesite el frontend."""

    id: UUID
    reserva_id: UUID
    recurso_id: UUID
    usuario_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoPrestamo
