from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.shared.database import Base


class ChecklistModel(Base):
    """Tabla prestamos.checklists (agregado Checklist)."""

    __tablename__ = "checklists"
    __table_args__ = {"schema": "prestamos"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    prestamo_id: Mapped[UUID] = mapped_column()
    tipo: Mapped[TipoChecklist] = mapped_column(SAEnum(TipoChecklist, native_enum=False, length=30))
    fecha_inspeccion: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str] = mapped_column(Text)
    fotos_urls: Mapped[list[str]] = mapped_column(ARRAY(Text).with_variant(JSON(), "sqlite"))
    completo: Mapped[bool] = mapped_column()
