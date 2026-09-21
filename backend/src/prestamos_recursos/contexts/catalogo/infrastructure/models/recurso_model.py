from uuid import UUID

from sqlalchemy import Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.shared.database import Base


class RecursoModel(Base):
    """Tabla catalogo.recursos (agregado Recurso)."""

    __tablename__ = "recursos"
    __table_args__ = {"schema": "catalogo"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    descripcion: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(255))
    estado: Mapped[EstadoRecurso] = mapped_column(SAEnum(EstadoRecurso, native_enum=False, length=30))
    marca: Mapped[str] = mapped_column(String(255))
    modelo: Mapped[str] = mapped_column(String(255))
    numero_serie: Mapped[str] = mapped_column(String(255))
    color: Mapped[str] = mapped_column(String(255))
    estado_fisico: Mapped[str] = mapped_column(String(255))
    foto_url: Mapped[str] = mapped_column(String(255))
