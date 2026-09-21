from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.shared.database import Base


class PrestamoModel(Base):
    """Tabla prestamos.prestamos (agregado Prestamo)."""

    __tablename__ = "prestamos"
    __table_args__ = {"schema": "prestamos"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    reserva_id: Mapped[UUID] = mapped_column()
    recurso_id: Mapped[UUID] = mapped_column()
    usuario_id: Mapped[UUID] = mapped_column()
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[EstadoPrestamo] = mapped_column(SAEnum(EstadoPrestamo, native_enum=False, length=30))
