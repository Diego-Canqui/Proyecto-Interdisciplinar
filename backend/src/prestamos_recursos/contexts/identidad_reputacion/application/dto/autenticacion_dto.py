from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic.types import StringConstraints

from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import UsuarioDTO
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario

# Validaciones de string con constraints
NombreStr = Annotated[str, StringConstraints(max_length=100, min_length=1)]
CorreoStr = Annotated[EmailStr, StringConstraints(max_length=255)]
TelefonoStr = Annotated[
    str | None, StringConstraints(pattern=r"^\+?[0-9\s-]{7,20}$", max_length=20)
]


def validar_password_complejidad(v: str) -> str:
    """Valida que la contraseña tenga al menos 8 chars, 1 mayúscula, 1 minúscula, 1 dígito."""
    if len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if not any(c.islower() for c in v):
        raise ValueError("La contraseña debe contener al menos una minúscula")
    if not any(c.isupper() for c in v):
        raise ValueError("La contraseña debe contener al menos una mayúscula")
    if not any(c.isdigit() for c in v):
        raise ValueError("La contraseña debe contener al menos un dígito")
    return v


class CrearUsuarioDTO(BaseModel):
    """DTO para crear un nuevo usuario (registro)."""

    nombre: NombreStr
    correo: CorreoStr
    telefono: TelefonoStr = None
    password: Annotated[str, Field(min_length=8)]
    roles: list[RolUsuario] | None = None

    @field_validator("password")
    @classmethod
    def _validar_password(cls, v: str) -> str:
        return validar_password_complejidad(v)


class LoginDTO(BaseModel):
    """DTO para login de usuario."""

    correo: CorreoStr
    password: str  # No validamos complejidad aquí, solo que no esté vacío


class TokenDTO(BaseModel):
    """DTO de respuesta con token JWT y datos del usuario."""

    token: str
    usuario: UsuarioDTO

    model_config = {"from_attributes": True}