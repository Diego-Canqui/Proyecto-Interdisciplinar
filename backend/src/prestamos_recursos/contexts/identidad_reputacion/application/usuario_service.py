from __future__ import annotations

from typing import Any
from uuid import UUID

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

    def __init__(
        self,
        usuario_repository: UsuarioRepository,
        reserva_service: Any | None = None,
        prestamo_service: Any | None = None,
    ) -> None:
        self._usuario_repository = usuario_repository
        self._reserva_service = reserva_service
        self._prestamo_service = prestamo_service

    def crear_usuario(
        self, datos: CrearUsuarioDTO, actor: UsuarioDTO | None = None
    ) -> UsuarioDTO:
        """
        Crea un usuario por la vía de gestión con una contraseña utilizable (RF-16/RF-09).

        - Si actor is not None y es solo GESTOR_ALMACEN, solo puede asignar roles solicitantes (403).
        - 409 si el correo ya está registrado (mismo patrón que el registro público).
        - Reutiliza `Usuario.crear_con_password` (hash bcrypt de la factory, sin duplicarlo).
        - Los roles del DTO tienen default [ESTUDIANTE].
        """
        if actor is not None:
            roles_actor = {RolUsuario(r) for r in actor.roles}
            if RolUsuario.ADMINISTRADOR_SISTEMA not in roles_actor:
                roles_solicitados = datos.roles or []
                roles_gestion = {
                    RolUsuario.GESTOR_ALMACEN,
                    RolUsuario.ADMINISTRADOR_SISTEMA,
                }
                if any(rol in roles_gestion for rol in roles_solicitados):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="El gestor de almacén solo puede asignar roles solicitantes",
                    )

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

    def cambiar_rol_usuario(
        self, id_usuario: UUID, nuevo_rol: RolUsuario, actor: UsuarioDTO
    ) -> UsuarioDTO:
        """RF-10: Cambia el rol de un usuario existente con autoprotección para administradores."""
        usuario = self._usuario_repository.obtener_por_id(id_usuario)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
            )

        if id_usuario == actor.id and nuevo_rol != RolUsuario.ADMINISTRADOR_SISTEMA:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes quitarte el rol de administrador a ti mismo",
            )

        usuario.cambiar_roles([nuevo_rol])
        self._usuario_repository.guardar(usuario)
        return self._a_dto(usuario)

    def cambiar_estado_usuario(
        self, id_usuario: UUID, estado: bool, actor: UsuarioDTO
    ) -> UsuarioDTO:
        """RF-11: Activa o desactiva la cuenta con autoprotección para administradores."""
        usuario = self._usuario_repository.obtener_por_id(id_usuario)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
            )

        if id_usuario == actor.id and not estado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes desactivar tu propia cuenta",
            )

        usuario.establecer_estado(estado)
        self._usuario_repository.guardar(usuario)
        return self._a_dto(usuario)

    def eliminar_usuario(self, id_usuario: UUID, actor: UsuarioDTO) -> None:
        """RF-12: Elimina un usuario sin reservas activas ni préstamos en curso."""
        usuario = self._usuario_repository.obtener_por_id(id_usuario)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
            )

        if id_usuario == actor.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes eliminar tu propia cuenta",
            )

        reservas_activas = self._contar_reservas_activas(id_usuario)
        prestamos_en_curso = self._contar_prestamos_en_curso(id_usuario)

        if reservas_activas + prestamos_en_curso > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede eliminar un usuario con reservas activas o préstamos en curso",
            )

        self._usuario_repository.eliminar(id_usuario)

    def _contar_reservas_activas(self, id_usuario: UUID) -> int:
        if self._reserva_service is None:
            return 0
        if hasattr(self._reserva_service, "contar_reservas_activas_usuario"):
            return int(self._reserva_service.contar_reservas_activas_usuario(id_usuario))
        if hasattr(self._reserva_service, "obtener_por_usuario"):
            reservas = self._reserva_service.obtener_por_usuario(id_usuario)
            activas = 0
            for r in reservas:
                est = getattr(r, "estado", None)
                val = est.value if hasattr(est, "value") else str(est)
                if val in ("PENDIENTE", "CONFIRMADA"):
                    activas += 1
            return activas
        return 0

    def _contar_prestamos_en_curso(self, id_usuario: UUID) -> int:
        if self._prestamo_service is None:
            return 0
        if hasattr(self._prestamo_service, "contar_prestamos_en_curso"):
            return int(self._prestamo_service.contar_prestamos_en_curso(id_usuario))
        if hasattr(self._prestamo_service, "consultar_historial"):
            prestamos = self._prestamo_service.consultar_historial(id_usuario)
            en_curso = 0
            for p in prestamos:
                est = getattr(p, "estado", None)
                val = est.value if hasattr(est, "value") else str(est)
                if val in ("ACTIVO", "ENTREGADO", "VENCIDO"):
                    en_curso += 1
            return en_curso
        return 0

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

