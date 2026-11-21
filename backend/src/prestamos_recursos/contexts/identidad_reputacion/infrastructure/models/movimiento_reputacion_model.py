from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_movimiento_reputacion import (
    TipoMovimientoReputacion,
)
from prestamos_recursos.shared.database import Base


class MovimientoReputacionModel(Base):
    """Tabla identidad_reputacion.movimientos_reputacion (bitácora append-only)."""

    __tablename__ = "movimientos_reputacion"
    __table_args__ = (
        Index(
            "ix_movimientos_reputacion_usuario_fecha_seq",
            "usuario_id",
            "fecha_movimiento",
            "numero_secuencia",
        ),
        Index(
            "ix_movimientos_reputacion_fecha_seq",
            "fecha_movimiento",
            "numero_secuencia",
        ),
        {"schema": "identidad_reputacion"},
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identidad_reputacion.usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[TipoMovimientoReputacion] = mapped_column(
        SAEnum(TipoMovimientoReputacion, native_enum=False, length=50),
        nullable=False,
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    puntaje_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    variacion_puntos: Mapped[int] = mapped_column(Integer, nullable=False)
    puntaje_resultante: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_movimiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    numero_secuencia: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sancion_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identidad_reputacion.sancion.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Referencias entre contextos por UUID simple sin FK inter-esquema (aislamiento DDD)
    prestamo_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    reserva_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    recurso_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    recurso_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
