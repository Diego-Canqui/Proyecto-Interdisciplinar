from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.shared.database import Base


class PerfilReputacionModel(Base):
    """Tabla identidad_reputacion.perfiles_reputacion (agregado PerfilReputacion)."""

    __tablename__ = "perfiles_reputacion"
    __table_args__ = (
        UniqueConstraint("usuario_id", name="uq_perfil_reputacion_usuario_id"),
        {"schema": "identidad_reputacion"},
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identidad_reputacion.usuario.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    puntos: Mapped[int] = mapped_column(default=500, nullable=False)
    nivel: Mapped[NivelReputacion] = mapped_column(
        SAEnum(NivelReputacion, native_enum=False, length=30),
        default=NivelReputacion.NORMAL,
        nullable=False,
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relación 1:N con SancionModel (cascade delete-orphan)
    sanciones: Mapped[list["SancionModel"]] = relationship(
        "SancionModel",
        back_populates="perfil",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SancionModel(Base):
    """Tabla identidad_reputacion.sancion (entidad Sancion, parte del agregado PerfilReputacion)."""

    __tablename__ = "sancion"
    __table_args__ = ({"schema": "identidad_reputacion"},)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    perfil_reputacion_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identidad_reputacion.perfiles_reputacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[TipoSancion] = mapped_column(
        SAEnum(TipoSancion, native_enum=False, length=30), nullable=False
    )
    puntos_descuento: Mapped[int] = mapped_column(nullable=False)
    monto_descuento: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal(0), nullable=False
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_aplicacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    activa: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relación N:1 hacia PerfilReputacionModel
    perfil: Mapped["PerfilReputacionModel"] = relationship(
        "PerfilReputacionModel", back_populates="sanciones"
    )