from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion
from prestamos_recursos.shared.database import Base


class PerfilReputacionModel(Base):
    """Tabla identidad.perfiles_reputacion (agregado PerfilReputacion)."""

    __tablename__ = "perfiles_reputacion"
    __table_args__ = {"schema": "identidad"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column()
    puntos: Mapped[int] = mapped_column()
    nivel: Mapped[NivelReputacion] = mapped_column(SAEnum(NivelReputacion, native_enum=False, length=30))
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True))
