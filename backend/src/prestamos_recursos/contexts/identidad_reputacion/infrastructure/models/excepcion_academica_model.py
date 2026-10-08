from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.shared.database import Base


class ExcepcionAcademicaModel(Base):
    """Tabla identidad_reputacion.excepciones_academicas (agregado ExcepcionAcademica)."""

    __tablename__ = "excepciones_academicas"
    __table_args__ = ({"schema": "identidad_reputacion"},)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identidad_reputacion.usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activa: Mapped[bool] = mapped_column(default=True, nullable=False)