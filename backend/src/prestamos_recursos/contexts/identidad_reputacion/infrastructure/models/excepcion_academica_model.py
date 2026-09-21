from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.shared.database import Base


class ExcepcionAcademicaModel(Base):
    """Tabla identidad.excepciones_academicas (agregado ExcepcionAcademica)."""

    __tablename__ = "excepciones_academicas"
    __table_args__ = {"schema": "identidad"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column()
    motivo: Mapped[str] = mapped_column(Text)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    activa: Mapped[bool] = mapped_column()
