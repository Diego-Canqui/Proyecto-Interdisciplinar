"""«Boundary» ReservaController."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.catalogo.infrastructure.repositories import (
    SqlRecursoRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    get_current_user,
)
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_checklist_repository import (
    SqlChecklistRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_garantia_repository import (
    SqlGarantiaRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_prestamo_repository import (
    SqlPrestamoRepository,
)
from prestamos_recursos.contexts.reservas.application.dto.reserva_dto import (
    CrearReservaDTO,
    ReservaDTO,
)
from prestamos_recursos.contexts.reservas.application.reserva_service import ReservaService
from prestamos_recursos.contexts.reservas.infrastructure.repositories.sql_reserva_repository import (
    SqlReservaRepository,
)
from prestamos_recursos.shared.database import get_session

router = APIRouter(prefix="/reservas", tags=["Reservas"])


def obtener_servicio(sesion: Annotated[Session, Depends(get_session)]) -> ReservaService:
    prestamos = PrestamoService(
        SqlPrestamoRepository(sesion),
        SqlChecklistRepository(sesion),
        SqlGarantiaRepository(sesion),
        recurso_repository=SqlRecursoRepository(sesion),
    )
    return ReservaService(SqlReservaRepository(sesion), prestamos)


ServicioReservas = Annotated[ReservaService, Depends(obtener_servicio)]
UsuarioAutenticado = Annotated[UsuarioDTO, Depends(get_current_user)]


@router.post("", response_model=ReservaDTO, status_code=201)
def solicitar_reserva(
    datos: CrearReservaDTO,
    servicio: ServicioReservas,
    usuario: UsuarioAutenticado,
) -> ReservaDTO:
    if datos.usuario_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="no puedes crear una reserva para otro usuario",
        )
    try:
        return servicio.crear_reserva(datos)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/usuario/{id_usuario}", response_model=list[ReservaDTO])
def consultar_por_usuario(
    id_usuario: UUID,
    servicio: ServicioReservas,
    usuario: UsuarioAutenticado,
) -> list[ReservaDTO]:
    if id_usuario != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="no puedes consultar las reservas de otro usuario",
        )
    return servicio.obtener_por_usuario(id_usuario)


@router.get("/recurso/{id_recurso}/cola", response_model=list[ReservaDTO])
def consultar_cola(
    id_recurso: UUID,
    servicio: ServicioReservas,
    _: UsuarioAutenticado,
) -> list[ReservaDTO]:
    return servicio.obtener_cola_espera(id_recurso)


def _reserva_del_usuario(
    id_reserva: UUID,
    servicio: ServicioReservas,
    usuario: UsuarioDTO,
) -> ReservaDTO:
    try:
        reserva = servicio.obtener_reserva(id_reserva)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


    if reserva.usuario_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="no puedes acceder a una reserva de otro usuario",
        )
    return reserva


@router.get("/{id_reserva}", response_model=ReservaDTO)
def consultar_reserva(
    id_reserva: UUID,
    servicio: ServicioReservas,
    usuario: UsuarioAutenticado,
) -> ReservaDTO:
    return _reserva_del_usuario(id_reserva, servicio, usuario)


@router.patch("/{id_reserva}/confirmar", response_model=ReservaDTO)
def confirmar_reserva(
    id_reserva: UUID,
    servicio: ServicioReservas,
    usuario: UsuarioAutenticado,
) -> ReservaDTO:
    _reserva_del_usuario(id_reserva, servicio, usuario)
    try:
        return servicio.confirmar_reserva(id_reserva)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{id_reserva}/prestamo", status_code=status.HTTP_201_CREATED)
def solicitar_prestamo(
    id_reserva: UUID,
    servicio: ServicioReservas,
    usuario: UsuarioAutenticado,
) -> dict[str, str]:
    """Convierte una reserva confirmada en préstamo si el recurso está disponible."""
    _reserva_del_usuario(id_reserva, servicio, usuario)
    try:
        creado = servicio.convertir_a_prestamo(id_reserva)
    except ValueError as error:
        codigo = 404 if str(error) == "Recurso no encontrado" else 409
        raise HTTPException(status_code=codigo, detail=str(error)) from error
    if not creado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="la reserva debe estar confirmada para solicitar el préstamo",
        )
    return {"detalle": "Préstamo creado desde la reserva"}


@router.patch("/{id_reserva}/cancelar", response_model=ReservaDTO)
def cancelar_reserva(
    id_reserva: UUID,
    servicio: ServicioReservas,
    usuario: UsuarioAutenticado,
) -> ReservaDTO:
    _reserva_del_usuario(id_reserva, servicio, usuario)
    try:
        servicio.cancelar_reserva(id_reserva)
        return servicio.obtener_reserva(id_reserva)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
