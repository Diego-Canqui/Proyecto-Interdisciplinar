"""«Boundary» UsuarioController."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.usuario_service import (
    UsuarioService,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import (
    SqlUsuarioRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    require_roles,
)
from prestamos_recursos.shared.database import get_session

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:  # noqa: B008
    return UsuarioService(SqlUsuarioRepository(session))


@router.post("", response_model=UsuarioDTO, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: CrearUsuarioDTO,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.GESTOR_ALMACEN, RolUsuario.ADMINISTRADOR_SISTEMA)),  # noqa: B008
    service: UsuarioService = Depends(get_usuario_service),  # noqa: B008
) -> UsuarioDTO:
    """
    Crea un usuario (solo GESTOR_ALMACEN o ADMINISTRADOR_SISTEMA) (RF-16/RF-17).

    Requiere header: Authorization: Bearer <token> con rol de gestión
    Body: { "nombre": str, "correo": email, "telefono": str?, "password": str, "roles": [RolUsuario]? }

    Retorna 201 con UsuarioDTO (el usuario creado, sin password_hash).
    Lanza 401 si token inválido, 403 si no tiene rol requerido, 409 si el correo ya
    existe y 422 si la contraseña no cumple la complejidad del registro.
    """
    return service.crear_usuario(datos)


@router.get("", response_model=list[UsuarioDTO])
def listar_usuarios(
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.GESTOR_ALMACEN, RolUsuario.ADMINISTRADOR_SISTEMA)),  # noqa: B008
    service: UsuarioService = Depends(get_usuario_service),  # noqa: B008
) -> list[UsuarioDTO]:
    """
    Lista todos los usuarios (solo GESTOR_ALMACEN o ADMINISTRADOR_SISTEMA) (RF-17).

    Requiere header: Authorization: Bearer <token> con rol de gestión

    Retorna 200 con la lista de UsuarioDTO (sin password_hash).
    Lanza 401 si token inválido, 403 si no tiene rol requerido.
    """
    return service.listar_usuarios()
