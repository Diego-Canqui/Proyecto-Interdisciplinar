from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.catalogo.domain.enums import EstadoRecurso
from prestamos_recursos.shared.database import Base


class RecursoModel(Base):
    """Modelo SQLAlchemy correspondiente para la tabla de base de datos de recursos."""

    __tablename__ = "recursos"
    __table_args__ = {"schema": "catalogo"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoRecurso] = mapped_column(
        SAEnum(EstadoRecurso, native_enum=False, length=30), nullable=False
    )
    marca: Mapped[str] = mapped_column(String(255), nullable=False)
    modelo: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_serie: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(255), nullable=False)
    estado_fisico: Mapped[str] = mapped_column(String(255), nullable=False)
    foto_url: Mapped[str] = mapped_column(String(255), nullable=False)
