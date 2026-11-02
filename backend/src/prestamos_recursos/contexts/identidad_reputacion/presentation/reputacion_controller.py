"""«Boundary» ReputacionController."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import (
    AplicarSancionDTO,
    ElegibilidadDTO,
    ExcepcionAcademicaDTO,
    PerfilGestionDTO,
    PerfilReputacionDTO,
    RegistrarExcepcionDTO,
    ResultadoAmnistiaDTO,
    SancionDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import UsuarioDTO
from prestamos_recursos.contexts.identidad_reputacion.application.excepciones import (
    ExcepcionNoEncontrada,
    SancionInvalida,
    UsuarioNoEncontrado,
)
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
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import (
    SqlUsuarioRepository,
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
        SqlUsuarioRepository(session),
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


@router.get("/elegibilidad", response_model=ElegibilidadDTO)
def obtener_elegibilidad(
    usuario: UsuarioDTO = Depends(get_current_user),  # noqa: B008
    service: ReputacionService = Depends(get_reputacion_service),  # noqa: B008
) -> ElegibilidadDTO:
    """
    Consulta la elegibilidad para préstamo del usuario autenticado (RF-21).

    Requiere header: Authorization: Bearer <token>

    Retorna 200 con ElegibilidadDTO (elegible y, si no lo es, la razón con el tipo
    de la sanción bloqueante y su fecha de fin).
    Lanza 401 si token inválido, expirado o usuario no existe.
    """
    return service.obtener_elegibilidad(usuario.id)


@router.get("/usuarios/{usuario_id}/perfil", response_model=PerfilGestionDTO)
def obtener_perfil_gestion(
    usuario_id: UUID,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN)),  # noqa: B008
    service: ReputacionService = Depends(get_reputacion_service),  # noqa: B008
) -> PerfilGestionDTO:
    """
    Obtiene la ficha de reputación de un tercero (solo ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN) (RF-04).

    Requiere header: Authorization: Bearer <token> con rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN

    Retorna 200 con PerfilGestionDTO (puntaje, nivel, fecha_actualizacion, sanciones y
    excepciones con su estado). Es de solo lectura: un usuario sin perfil devuelve su
    estado inicial (500, NORMAL, sin sanciones) sin crearlo y con sus excepciones reales.
    Lanza 401 si token inválido o expirado, 403 si no tiene rol requerido y 404 si el
    usuario no existe.
    """
    try:
        return service.obtener_perfil_gestion(usuario_id)
    except UsuarioNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/sanciones", response_model=SancionDTO, status_code=status.HTTP_201_CREATED)
def aplicar_sancion(
    datos: AplicarSancionDTO,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN)),  # noqa: B008
    service: ReputacionService = Depends(get_reputacion_service),  # noqa: B008
) -> SancionDTO:
    """
    Aplica una sanción a un usuario (solo ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN).

    Requiere header: Authorization: Bearer <token> con rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN
    Body: { "usuario_id": UUID, "tipo": TipoSancion, "motivo": str, "monto_opcional": Decimal?,
            "dias_retardo": int? }

    Retorna 201 con SancionDTO (la sanción real aplicada y persistida).
    Lanza 401 si token inválido, 403 si no tiene rol requerido, 404 si el usuario
    sancionado no existe (RF-23) y 422 si las premisas del tipo no son válidas (RF-06/RF-07).
    """
    try:
        return service.aplicar_sancion(
            datos.usuario_id,
            datos.tipo,
            datos.motivo,
            datos.monto_opcional,
            datos.dias_retardo,
        )
    except UsuarioNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SancionInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


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
    Lanza 401 si token inválido, 403 si no tiene rol requerido y 404 si el usuario
    no existe (RF-23).
    """
    try:
        return service.registrar_excepcion(
            datos.usuario_id, datos.motivo, datos.fecha_inicio, datos.fecha_fin
        )
    except UsuarioNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/excepciones/{excepcion_id}/anular", response_model=ExcepcionAcademicaDTO)
def anular_excepcion(
    excepcion_id: UUID,
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN)),  # noqa: B008
    service: ReputacionService = Depends(get_reputacion_service),  # noqa: B008
) -> ExcepcionAcademicaDTO:
    """
    Anula una excepción académica (solo ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN) (RF-22).

    Requiere header: Authorization: Bearer <token> con rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN
    Path: id de la excepción a anular.

    Retorna 200 con ExcepcionAcademicaDTO (la excepción anulada; idempotente).
    Lanza 401 si token inválido, 403 si no tiene rol requerido y 404 si la
    excepción no existe (RF-22).
    """
    try:
        return service.anular_excepcion(excepcion_id)
    except ExcepcionNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/amnistia", response_model=ResultadoAmnistiaDTO)
def ejecutar_amnistia(
    usuario: UsuarioDTO = Depends(require_roles(RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN)),  # noqa: B008
    service: ReputacionService = Depends(get_reputacion_service),  # noqa: B008
) -> ResultadoAmnistiaDTO:
    """
    Ejecuta la amnistía mensual (solo ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN) (RF-13).

    Requiere header: Authorization: Bearer <token> con rol ADMINISTRADOR_SISTEMA o GESTOR_ALMACEN

    Retorna 200 con ResultadoAmnistiaDTO (perfiles_premiados; 0 es un valor válido).
    Lanza 401 si token inválido, 403 si no tiene rol requerido.
    """
    return ResultadoAmnistiaDTO(perfiles_premiados=service.ejecutar_amnistia_mensual())