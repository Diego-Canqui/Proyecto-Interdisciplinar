"""«Boundary» UsuarioController."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    CrearUsuarioDTO,
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.usuario_service import UsuarioService
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import (
    SqlUsuarioRepository,
)
from prestamos_recursos.shared.database import get_session

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    return UsuarioService(SqlUsuarioRepository(session))


@router.post("", response_model=UsuarioDTO)
def crear_usuario(
    datos: CrearUsuarioDTO, service: UsuarioService = Depends(get_usuario_service)
) -> UsuarioDTO:
    return service.crear_usuario(datos)


@router.get("", response_model=list[UsuarioDTO])
def listar_usuarios(service: UsuarioService = Depends(get_usuario_service)) -> list[UsuarioDTO]:
    return service.listar_usuarios()
