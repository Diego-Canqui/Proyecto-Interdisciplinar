"""Dependencias de seguridad para la API de autenticación."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import (
    AutenticacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.gestion_acceso_service import (
    GestionAccesoService,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import (
    SqlUsuarioRepository,
)
from prestamos_recursos.shared.database import get_session

# Esquema OAuth2 para extraer el token del header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_autenticacion_service(session: Session = Depends(get_session)) -> AutenticacionService:  # noqa: B008
    """Factory para inyectar AutenticacionService con repositorio real."""
    return AutenticacionService(SqlUsuarioRepository(session))


def get_gestion_acceso_service(
    auth_service: AutenticacionService = Depends(get_autenticacion_service),  # noqa: B008
) -> GestionAccesoService:
    """Factory para inyectar GestionAccesoService delegando a AutenticacionService."""
    return GestionAccesoService(auth_service)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    gestion_acceso: GestionAccesoService = Depends(get_gestion_acceso_service),  # noqa: B008
) -> UsuarioDTO:
    """
    Dependencia para obtener el usuario autenticado a partir del token JWT.

    Valida el token, extrae el sub (UUID), busca el usuario y retorna UsuarioDTO.
    Lanza HTTPException 401 si el token es inválido, expirado o el usuario no existe.
    """
    usuario = gestion_acceso.obtener_usuario_autenticado(token)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario