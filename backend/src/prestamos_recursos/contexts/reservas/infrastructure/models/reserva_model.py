from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.reservas.domain.enums.estado_reserva import EstadoReserva
from prestamos_recursos.shared.database import Base


class ReservaModel(Base):
    """Tabla reservas.reservas (agregado Reserva)."""

    __tablename__ = "reservas"
    __table_args__ = {"schema": "reservas"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column()
    recurso_id: Mapped[UUID] = mapped_column()
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[EstadoReserva] = mapped_column(SAEnum(EstadoReserva, native_enum=False, length=30))
