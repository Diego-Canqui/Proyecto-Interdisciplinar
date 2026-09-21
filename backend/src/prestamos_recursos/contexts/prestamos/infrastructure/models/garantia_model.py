from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.shared.database import Base


class GarantiaModel(Base):
    """Tabla prestamos.garantias (agregado Garantia)."""

    __tablename__ = "garantias"
    __table_args__ = {"schema": "prestamos"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    prestamo_id: Mapped[UUID] = mapped_column()
    tipo: Mapped[TipoGarantia] = mapped_column(SAEnum(TipoGarantia, native_enum=False, length=30))
    estado: Mapped[EstadoGarantia] = mapped_column(SAEnum(EstadoGarantia, native_enum=False, length=30))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_liberacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    compromiso_contenido: Mapped[str] = mapped_column(Text)
    compromiso_fecha_firma: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    compromiso_firma_url: Mapped[str] = mapped_column(String(255))
    compromiso_testigo: Mapped[str] = mapped_column(String(255))
