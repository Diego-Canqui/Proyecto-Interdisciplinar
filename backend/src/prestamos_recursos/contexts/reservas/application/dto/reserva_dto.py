from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva


class CrearReservaDTO(BaseModel):
    usuario_id: UUID
    recurso_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime

    @model_validator(mode="after")
    def validar_fechas(self) -> "CrearReservaDTO":
        inicio_con_zona = self.fecha_inicio.utcoffset() is not None
        fin_con_zona = self.fecha_fin.utcoffset() is not None
        if inicio_con_zona != fin_con_zona:
            raise ValueError("ambas fechas deben incluir zona horaria o ninguna")
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("la fecha de fin debe ser posterior a la fecha de inicio")
        return self


class ReservaDTO(BaseModel):
    """Datos de una reserva para devolver al cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    usuario_id: UUID
    recurso_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoReserva
