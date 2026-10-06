from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import (
    AutenticacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import UsuarioDTO
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario


class GestionAccesoService:
    """«Service» GestionAccesoService."""

    def __init__(self, autenticacion_service: AutenticacionService) -> None:
        self._autenticacion_service = autenticacion_service

    def autenticar_jwt(self, token: str) -> bool:
        """Valida un token JWT y retorna True si es válido, False en caso contrario. RF-10, RF-11"""
        usuario_id = self._autenticacion_service.validar_token(token)
        return usuario_id is not None

    def verificar_permisos(self, id_usuario: UUID, rol: RolUsuario) -> bool:
        raise NotImplementedError

    def obtener_usuario_autenticado(self, token: str) -> UsuarioDTO | None:
        """Obtiene el usuario autenticado a partir de un token JWT. RF-10, RF-11"""
        return self._autenticacion_service.obtener_usuario_por_token(token)
