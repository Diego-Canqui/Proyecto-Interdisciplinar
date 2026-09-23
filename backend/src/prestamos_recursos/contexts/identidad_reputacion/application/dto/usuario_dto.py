from uuid import UUID

from pydantic import BaseModel

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario


class UsuarioDTO(BaseModel):
    """DTO UsuarioDTO. TODO: ajustar los campos a lo que necesite el frontend."""

    id: UUID
    nombre: str
    correo: str
    telefono: str
    estado: bool
    roles: list[RolUsuario]


class CrearUsuarioDTO(BaseModel):
    """Datos necesarios para registrar un nuevo Usuario."""

    nombre: str
    correo: str
    telefono: str
    roles: list[RolUsuario] = []
