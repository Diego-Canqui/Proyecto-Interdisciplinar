from __future__ import annotations

from dataclasses import dataclass, field

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Usuario(BaseEntity):
    """«Aggregate Root» Usuario."""

    nombre: str
    correo: str
    telefono: str
    estado: bool
    roles: set[RolUsuario] = field(default_factory=set)

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
