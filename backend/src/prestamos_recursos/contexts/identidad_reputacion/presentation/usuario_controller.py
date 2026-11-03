"""«Boundary» UsuarioController."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    ActualizarEstadoUsuarioDTO,
    ActualizarRolUsuarioDTO,
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


def get_usuario_service(
    session: Session = Depends(get_session, scope="function"),  # noqa: B008
) -> UsuarioService:
    from prestamos_recursos.contexts.catalogo.infrastructure.repositories import (
        SqlRecursoRepository,
    )
    from prestamos_recursos.contexts.identidad_reputacion.application.reputacion_service import (
        ReputacionService,
    )
    from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_excepcion_academica_repository import (
        SqlExcepcionAcademicaRepository,
    )
    from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_perfil_reputacion_repository import (
        SqlPerfilReputacionRepository,
    )
    from prestamos_recursos.contexts.prestamos.application.prestamo_service import (
        PrestamoService,
    )
    from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_checklist_repository import (
        SqlChecklistRepository,
    )
    from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_garantia_repository import (
        SqlGarantiaRepository,
    )
    from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_prestamo_repository import (
        SqlPrestamoRepository,
    )
    from prestamos_recursos.contexts.reservas.application.reserva_service import (
        ReservaService,
    )
    from prestamos_recursos.contexts.reservas.infrastructure.repositories.sql_reserva_repository import (
        SqlReservaRepository,
    )

    usuario_repo = SqlUsuarioRepository(session)
    recurso_repo = SqlRecursoRepository(session)
    checklist_repo = SqlChecklistRepository(session)
    garantia_repo = SqlGarantiaRepository(session)
    prestamo_repo = SqlPrestamoRepository(session)
    perfil_repo = SqlPerfilReputacionRepository(session)
    excepcion_repo = SqlExcepcionAcademicaRepository(session)

    reputacion_service = ReputacionService(
        perfil_reputacion_repository=perfil_repo,
        excepcion_academica_repository=excepcion_repo,
        usuario_repository=usuario_repo,
    )
    prestamo_service = PrestamoService(
        prestamo_repository=prestamo_repo,
        checklist_repository=checklist_repo,
        garantia_repository=garantia_repo,
        reputacion_service=reputacion_service,
        recurso_repository=recurso_repo,
    )
    reserva_repo = SqlReservaRepository(session)
    reserva_service = ReservaService(
        reserva_repository=reserva_repo,
        prestamo_service=prestamo_service,
        reputacion_service=reputacion_service,
    )
    return UsuarioService(
        usuario_repository=usuario_repo,
        reserva_service=reserva_service,
        prestamo_service=prestamo_service,
    )


@router.post("", response_model=UsuarioDTO, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: CrearUsuarioDTO,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.GESTOR_ALMACEN, RolUsuario.ADMINISTRADOR_SISTEMA)),  # noqa: B008
    service: UsuarioService = Depends(get_usuario_service),  # noqa: B008
) -> UsuarioDTO:
    """
    Crea un usuario (solo GESTOR_ALMACEN o ADMINISTRADOR_SISTEMA) (RF-16/RF-17/RF-09).

    Requiere header: Authorization: Bearer <token> con rol de gestión
    Body: { "nombre": str, "correo": email, "telefono": str?, "password": str, "roles": [RolUsuario]? }

    Retorna 201 con UsuarioDTO (el usuario creado, sin password_hash).
    Lanza 401 si token inválido, 403 si no tiene rol requerido o si GESTOR_ALMACEN intenta asignar roles de gestión,
    409 si el correo ya existe y 422 si la contraseña no cumple la complejidad del registro.
    """
    return service.crear_usuario(datos, actor=usuario)


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


@router.patch("/{id_usuario}/rol", response_model=UsuarioDTO)
def cambiar_rol_usuario(
    id_usuario: UUID,
    datos: ActualizarRolUsuarioDTO,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA)),  # noqa: B008
    service: UsuarioService = Depends(get_usuario_service),  # noqa: B008
) -> UsuarioDTO:
    """
    Cambia el rol de un usuario (solo ADMINISTRADOR_SISTEMA) (RF-10).

    403 si no es admin, 404 si el usuario no existe, 409 si el admin intenta quitarse a sí mismo ADMINISTRADOR_SISTEMA.
    """
    return service.cambiar_rol_usuario(id_usuario, datos.rol, actor=usuario)


@router.patch("/{id_usuario}/estado", response_model=UsuarioDTO)
def cambiar_estado_usuario(
    id_usuario: UUID,
    datos: ActualizarEstadoUsuarioDTO,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA)),  # noqa: B008
    service: UsuarioService = Depends(get_usuario_service),  # noqa: B008
) -> UsuarioDTO:
    """
    Activa o desactiva la cuenta de un usuario (solo ADMINISTRADOR_SISTEMA) (RF-11).

    403 si no es admin, 404 si el usuario no existe, 409 si el admin intenta desactivar su propia cuenta.
    """
    return service.cambiar_estado_usuario(id_usuario, datos.estado, actor=usuario)


@router.delete("/{id_usuario}")
def eliminar_usuario(
    id_usuario: UUID,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA)),  # noqa: B008
    service: UsuarioService = Depends(get_usuario_service),  # noqa: B008
) -> dict[str, str]:
    """
    Elimina un usuario sin reservas activas ni préstamos en curso (solo ADMINISTRADOR_SISTEMA) (RF-12).

    403 si no es admin, 404 si no existe, 409 si intenta autoeliminarse o tiene operaciones activas.
    """
    service.eliminar_usuario(id_usuario, actor=usuario)
    return {"detalle": "Usuario eliminado correctamente"}

