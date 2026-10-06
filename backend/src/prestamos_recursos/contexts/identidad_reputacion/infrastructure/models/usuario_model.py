from uuid import UUID

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.shared.database import Base


class UsuarioModel(Base):
    """Tabla identidad_reputacion.usuario (agregado Usuario)."""

    __tablename__ = "usuario"
    __table_args__ = {"schema": "identidad_reputacion"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    correo: Mapped[str] = mapped_column(String(255), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    estado: Mapped[bool] = mapped_column(default=True)
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), default=list
    )
