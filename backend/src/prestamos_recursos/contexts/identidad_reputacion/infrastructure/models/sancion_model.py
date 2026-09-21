from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.shared.database import Base


class SancionModel(Base):
    """Tabla identidad.sanciones (agregado Sancion)."""

    __tablename__ = "sanciones"
    __table_args__ = {"schema": "identidad"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    perfil_reputacion_id: Mapped[UUID] = mapped_column()
    tipo: Mapped[TipoSancion] = mapped_column(SAEnum(TipoSancion, native_enum=False, length=30))
    puntos_descuento: Mapped[int] = mapped_column()
    monto_descuento: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    motivo: Mapped[str] = mapped_column(Text)
    fecha_aplicacion: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    activa: Mapped[bool] = mapped_column()
