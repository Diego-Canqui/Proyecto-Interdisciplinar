from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.catalogo.domain.enums import EstadoRecurso
from prestamos_recursos.shared.database import Base


class RecursoModel(Base):
    """Modelo SQLAlchemy correspondiente para la tabla de base de datos de recursos."""

    __tablename__ = "recursos"
    __table_args__ = (
        None if os.getenv("TESTING") == "1" else {"schema": "catalogo"}
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoRecurso] = mapped_column(
        SAEnum(EstadoRecurso, native_enum=False, length=30), nullable=False
    )
    marca: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    color: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estado_fisico: Mapped[str] = mapped_column(String(255), nullable=False)
    foto_url: Mapped[str] = mapped_column(String(255), nullable=False)
    especificaciones: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
