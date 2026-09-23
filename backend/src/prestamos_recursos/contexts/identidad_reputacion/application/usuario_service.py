from __future__ import annotations

from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    CrearUsuarioDTO,
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import UsuarioRepository


class UsuarioService:
    """«Service» UsuarioService."""

    def __init__(self, usuario_repository: UsuarioRepository) -> None:
        self._usuario_repository = usuario_repository

    def crear_usuario(self, datos: CrearUsuarioDTO) -> UsuarioDTO:
        usuario = Usuario(
            nombre=datos.nombre,
            correo=datos.correo,
            telefono=datos.telefono,
            estado=True,
            roles=set(datos.roles),
        )
        self._usuario_repository.guardar(usuario)
        return self._a_dto(usuario)

    def listar_usuarios(self) -> list[UsuarioDTO]:
        return [self._a_dto(u) for u in self._usuario_repository.listar()]

    @staticmethod
    def _a_dto(usuario: Usuario) -> UsuarioDTO:
        return UsuarioDTO(
            id=usuario.id,
            nombre=usuario.nombre,
            correo=usuario.correo,
            telefono=usuario.telefono,
            estado=usuario.estado,
            roles=list(usuario.roles),
        )
