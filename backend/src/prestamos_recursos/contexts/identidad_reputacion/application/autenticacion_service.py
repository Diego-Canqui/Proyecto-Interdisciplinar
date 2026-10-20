from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import JWTError

from prestamos_recursos.config import settings
from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
    LoginDTO,
    TokenDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import (
    UsuarioRepository,
)


class AutenticacionService:
    """Servicio de aplicación para autenticación y gestión de tokens JWT."""

    def __init__(self, usuario_repo: UsuarioRepository) -> None:
        self._usuario_repo = usuario_repo

    def registrar_usuario(self, datos: CrearUsuarioDTO) -> TokenDTO:
        """Registra un nuevo usuario y devuelve token JWT + datos del usuario."""
        # Verificar si el correo ya existe
        usuario_existente = self._usuario_repo.obtener_por_correo(datos.correo)
        if usuario_existente is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Correo ya registrado"
            )

        # Crear usuario con password hasheado
        roles = datos.roles if datos.roles is not None else [RolUsuario.ESTUDIANTE]
        usuario = Usuario.crear_con_password(
            nombre=datos.nombre,
            correo=datos.correo,
            telefono=datos.telefono,
            password_plano=datos.password,
            roles=roles,
        )

        # Guardar en repositorio
        self._usuario_repo.guardar(usuario)

        # Generar JWT
        token = self._generar_token(usuario)

        return TokenDTO(token=token, usuario=UsuarioDTO.from_entity(usuario))

    def login(self, datos: LoginDTO) -> TokenDTO:
        """Autentica un usuario y devuelve token JWT + datos del usuario."""
        usuario = self._usuario_repo.obtener_por_correo(datos.correo)

        # Verificación genérica para no revelar si el usuario existe
        if usuario is None or not usuario.verificar_password(datos.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
            )

        # Generar JWT
        token = self._generar_token(usuario)

        return TokenDTO(token=token, usuario=UsuarioDTO.from_entity(usuario))

    def validar_token(self, token: str) -> UUID | None:
        """Valida un token JWT y devuelve el UUID del usuario (sub) o None si es inválido."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
            )
            sub = payload.get("sub")
            if sub is None:
                return None
            return UUID(sub)
        except (JWTError, ValueError):
            return None

    def obtener_usuario_por_token(self, token: str) -> UsuarioDTO | None:
        """Obtiene el usuario asociado a un token JWT válido."""
        usuario_id = self.validar_token(token)
        if usuario_id is None:
            return None

        usuario = self._usuario_repo.obtener_por_id(usuario_id)
        if usuario is None:
            return None

        return UsuarioDTO.from_entity(usuario)

    def _generar_token(self, usuario: Usuario) -> str:
        """Genera un token JWT con claims: sub, roles, exp, iat."""
        ahora = datetime.now(UTC)
        expiracion = ahora + timedelta(hours=settings.jwt_expiracion_horas or 24)

        roles_str = [rol.value for rol in usuario.roles]

        payload = {
            "sub": str(usuario.id),
            "roles": roles_str,
            "exp": expiracion,
            "iat": ahora,
        }

        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")