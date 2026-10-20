from __future__ import annotations

from fastapi import HTTPException, status

from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import (
    UsuarioRepository,
)


class UsuarioService:
    """«Service» UsuarioService."""

    def __init__(self, usuario_repository: UsuarioRepository) -> None:
        self._usuario_repository = usuario_repository

    def crear_usuario(self, datos: CrearUsuarioDTO) -> UsuarioDTO:
        """
        Crea un usuario por la vía de gestión con una contraseña utilizable (RF-16).

        - 409 si el correo ya está registrado (mismo patrón que el registro público)
        - Reutiliza `Usuario.crear_con_password` (hash bcrypt de la factory, sin duplicarlo)
        - Los roles del DTO tienen default [ESTUDIANTE]
        """
        usuario_existente = self._usuario_repository.obtener_por_correo(datos.correo)
        if usuario_existente is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Correo ya registrado"
            )

        roles = datos.roles if datos.roles is not None else [RolUsuario.ESTUDIANTE]
        usuario = Usuario.crear_con_password(
            nombre=datos.nombre,
            correo=datos.correo,
            telefono=datos.telefono,
            password_plano=datos.password,
            roles=roles,
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
