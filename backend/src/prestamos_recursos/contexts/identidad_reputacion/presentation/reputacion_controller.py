"""«Boundary» ReputacionController."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, status

from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import (
    AplicarSancionDTO,
    ExcepcionAcademicaDTO,
    PerfilReputacionDTO,
    RegistrarExcepcionDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import UsuarioDTO
from prestamos_recursos.contexts.identidad_reputacion.application.reputacion_service import (
    ReputacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_excepcion_academica_repository import (
    SqlExcepcionAcademicaRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_perfil_reputacion_repository import (
    SqlPerfilReputacionRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    get_current_user,
    get_session,
    require_roles,
)
from prestamos_recursos.shared.database import Session as DBSession

router = APIRouter(prefix="/reputacion", tags=["Reputación"])


def get_reputacion_service(session: DBSession = Depends(get_session)) -> ReputacionService:  # noqa: B008
    """Factory para inyectar ReputacionService con repositorios reales."""
    return ReputacionService(
        SqlPerfilReputacionRepository(session),
        SqlExcepcionAcademicaRepository(session),
    )


@router.get("/perfil", response_model=PerfilReputacionDTO)
def obtener_perfil(
    usuario: UsuarioDTO = Depends(get_current_user),  # noqa: B008
    service: ReputacionService = Depends(get_reputacion_service),  # noqa: B008
) -> PerfilReputacionDTO:
    """
    Obtiene el perfil de reputación del usuario autenticado.

    Requiere header: Authorization: Bearer <token>

    Retorna 200 con PerfilReputacionDTO (puntaje, nivel, sanciones, fecha_actualizacion).
    Lanza 401 si token inválido, expirado o usuario no existe.
    """
    return service.obtener_perfil(usuario.id)


@router.post("/sanciones", response_model=ExcepcionAcademicaDTO, status_code=status.HTTP_201_CREATED)
def aplicar_sancion(
    datos: AplicarSancionDTO,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN)),  # noqa: B008
    service: ReputacionService = Depends(get_reputacion_service),  # noqa: B008
) -> ExcepcionAcademicaDTO:
    """
    Aplica una sanción a un usuario (solo ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN).

    Requiere header: Authorization: Bearer <token> con rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN
    Body: { "usuario_id": UUID, "tipo": TipoSancion, "motivo": str }

    Retorna 201 con ExcepcionAcademicaDTO (la excepción creada como confirmación).
    Lanza 401 si token inválido, 403 si no tiene rol requerido.
    """
    service.aplicar_sancion(datos.usuario_id, datos.tipo, datos.motivo)

    # Retornar un DTO de confirmación (usamos ExcepcionAcademicaDTO como respuesta genérica)
    # En la práctica, podríamos crear un DTO específico de respuesta para sanción aplicada
    return ExcepcionAcademicaDTO(
        id=uuid4(),  # ID ficticio para confirmación
        usuario_id=datos.usuario_id,
        motivo=f"Sanción aplicada: {datos.tipo.value} - {datos.motivo}",
        fecha_inicio=datetime.now(UTC),
        fecha_fin=datetime.now(UTC),
        activa=True,
    )


@router.post("/excepciones", response_model=ExcepcionAcademicaDTO, status_code=status.HTTP_201_CREATED)
def registrar_excepcion(
    datos: RegistrarExcepcionDTO,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN)),  # noqa: B008
    service: ReputacionService = Depends(get_reputacion_service),  # noqa: B008
) -> ExcepcionAcademicaDTO:
    """
    Registra una excepción académica para un usuario (solo ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN).

    Requiere header: Authorization: Bearer <token> con rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN
    Body: { "usuario_id": UUID, "motivo": str, "fecha_inicio": datetime, "fecha_fin": datetime }

    Retorna 201 con ExcepcionAcademicaDTO.
    Lanza 401 si token inválido, 403 si no tiene rol requerido.
    """
    return service.registrar_excepcion(
        datos.usuario_id, datos.motivo, datos.fecha_inicio, datos.fecha_fin
    )