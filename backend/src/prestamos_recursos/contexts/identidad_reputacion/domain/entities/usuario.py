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

    def actualizar_perfil(self) -> None:
        raise NotImplementedError

    def cambiar_estado(self) -> None:
        raise NotImplementedError
