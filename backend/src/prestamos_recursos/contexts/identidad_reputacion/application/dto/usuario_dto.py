from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario


class UsuarioDTO(BaseModel):
    """DTO de usuario para respuestas (sin password_hash)."""

    id: UUID
    nombre: str
    correo: str
    telefono: str | None
    roles: list[RolUsuario]
    estado: bool

    @classmethod
    def from_entity(cls, usuario) -> UsuarioDTO:
        """Crea un UsuarioDTO desde una entidad Usuario del dominio."""
        return cls(
            id=usuario.id,
            nombre=usuario.nombre,
            correo=usuario.correo,
            telefono=usuario.telefono,
            roles=usuario.roles,
            estado=usuario.estado,
        )

    model_config = {"from_attributes": True}