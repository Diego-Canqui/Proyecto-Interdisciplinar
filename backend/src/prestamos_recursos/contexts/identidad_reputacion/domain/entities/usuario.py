from __future__ import annotations

from dataclasses import dataclass, field

import bcrypt

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import (
    RolUsuario,
)
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Usuario(BaseEntity):
    """«Aggregate Root» Usuario."""

    nombre: str
    correo: str
    telefono: str | None = None
    password_hash: str
    roles: list[RolUsuario] = field(default_factory=lambda: [RolUsuario.ESTUDIANTE])
    estado: bool = True

    @classmethod
    def crear_con_password(
        cls,
        nombre: str,
        correo: str,
        telefono: str | None,
        password_plano: str,
        roles: list[RolUsuario] | None = None,
    ) -> Usuario:
        """Crea un Usuario hasheando la contraseña con bcrypt (coste 12)."""
        password_bytes = password_plano.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")
        return cls(
            nombre=nombre,
            correo=correo,
            telefono=telefono,
            password_hash=password_hash,
            roles=roles if roles is not None else [RolUsuario.ESTUDIANTE],
            estado=True,
        )

    def verificar_password(self, password_plano: str) -> bool:
        """Verifica si la contraseña plana coincide con el hash almacenado."""
        password_bytes = password_plano.encode("utf-8")
        hash_bytes = self.password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)

    def actualizar_perfil(
        self,
        *,
        nombre: str | None = None,
        correo: str | None = None,
        telefono: str | None = None,
    ) -> None:
        if nombre is not None:
            self.nombre = nombre
        if correo is not None:
            self.correo = correo
        if telefono is not None:
            self.telefono = telefono

    def cambiar_estado(self) -> None:
        self.estado = not self.estado
