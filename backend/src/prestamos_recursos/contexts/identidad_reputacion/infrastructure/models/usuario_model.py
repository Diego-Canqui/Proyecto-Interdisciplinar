from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from prestamos_recursos.shared.database import Base

if TYPE_CHECKING:
    from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario


class UsuarioModel(Base):
    """Tabla identidad_reputacion.usuario (agregado Usuario)."""

    __tablename__ = "usuario"
    __table_args__ = ({"schema": "identidad_reputacion"},)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[bool] = mapped_column(default=True, nullable=False)
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), default=lambda: ["ESTUDIANTE"], nullable=False
    )

    def to_entity(self) -> Usuario:
        """Convierte el modelo SQLAlchemy a entidad de dominio."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import (
            RolUsuario,
        )

        return Usuario(
            id=self.id,
            nombre=self.nombre,
            correo=self.correo,
            telefono=self.telefono,
            password_hash=self.password_hash,
            estado=self.estado,
            roles=[RolUsuario(r) for r in self.roles],
        )

    @classmethod
    def from_entity(cls, usuario: Usuario) -> UsuarioModel:
        """Crea una instancia del modelo a partir de una entidad de dominio."""
        return cls(
            id=usuario.id,
            nombre=usuario.nombre,
            correo=usuario.correo,
            telefono=usuario.telefono,
            password_hash=usuario.password_hash,
            estado=usuario.estado,
            roles=[rol.value for rol in usuario.roles],
        )
