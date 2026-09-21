from uuid import UUID

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.shared.database import Base


class UsuarioModel(Base):
    """Tabla identidad.usuarios (agregado Usuario)."""

    __tablename__ = "usuarios"
    __table_args__ = {"schema": "identidad"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    correo: Mapped[str] = mapped_column(String(255))
    telefono: Mapped[str] = mapped_column(String(255))
    estado: Mapped[bool] = mapped_column()
    roles: Mapped[list[str]] = mapped_column(ARRAY(String(30)))
