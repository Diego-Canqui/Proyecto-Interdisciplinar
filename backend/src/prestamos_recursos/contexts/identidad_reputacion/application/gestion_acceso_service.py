from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import UsuarioDTO
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import UsuarioRepository


class GestionAccesoService:
    """«Service» GestionAccesoService."""

    def __init__(self, usuario_repository: UsuarioRepository) -> None:
        self._usuario_repository = usuario_repository

    def autenticar_jwt(self, token: str) -> bool:
        raise NotImplementedError

    def verificar_permisos(self, id_usuario: UUID, rol: RolUsuario) -> bool:
        raise NotImplementedError

    def obtener_usuario_autenticado(self) -> UsuarioDTO:
        raise NotImplementedError
