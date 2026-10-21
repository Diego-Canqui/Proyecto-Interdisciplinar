"""«Boundary» ReservaController."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
    return ReservaService(SqlReservaRepository(sesion))


ServicioReservas = Annotated[ReservaService, Depends(obtener_servicio)]


@router.post("", response_model=ReservaDTO, status_code=201)
def solicitar_reserva(datos: CrearReservaDTO, servicio: ServicioReservas) -> ReservaDTO:
    try:
        return servicio.crear_reserva(datos)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{id_reserva}", response_model=ReservaDTO)
def consultar_reserva(id_reserva: UUID, servicio: ServicioReservas) -> ReservaDTO:
    try:
        return servicio.obtener_reserva(id_reserva)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/usuario/{id_usuario}", response_model=list[ReservaDTO])
def consultar_por_usuario(id_usuario: UUID, servicio: ServicioReservas) -> list[ReservaDTO]:
    return servicio.obtener_por_usuario(id_usuario)


@router.patch("/{id_reserva}/confirmar", response_model=ReservaDTO)
def confirmar_reserva(id_reserva: UUID, servicio: ServicioReservas) -> ReservaDTO:
    try:
        return servicio.confirmar_reserva(id_reserva)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.patch("/{id_reserva}/cancelar", response_model=ReservaDTO)
def cancelar_reserva(id_reserva: UUID, servicio: ServicioReservas) -> ReservaDTO:
    try:
        servicio.cancelar_reserva(id_reserva)
        return servicio.obtener_reserva(id_reserva)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/recurso/{id_recurso}/cola", response_model=list[ReservaDTO])
def consultar_cola(id_recurso: UUID, servicio: ServicioReservas) -> list[ReservaDTO]:
    return servicio.obtener_cola_espera(id_recurso)
