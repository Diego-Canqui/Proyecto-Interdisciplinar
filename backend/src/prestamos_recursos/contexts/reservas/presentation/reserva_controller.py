"""«Boundary» ReservaController."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from prestamos_recursos.contexts.reservas.application.dto.reserva_dto import (
    CrearReservaDTO,
    ReservaDTO,
)
from prestamos_recursos.contexts.reservas.application.reserva_service import ReservaService
from prestamos_recursos.contexts.reservas.infrastructure.repositories.memoria_reserva_repository import (
    MemoriaReservaRepository,
)

router = APIRouter(prefix="/reservas", tags=["Reservas"])

# Una instancia por proceso para conservar las reservas entre peticiones.
_repositorio = MemoriaReservaRepository()


def obtener_servicio() -> ReservaService:
    return ReservaService(_repositorio)


ServicioReservas = Annotated[ReservaService, Depends(obtener_servicio)]


@router.post("", response_model=ReservaDTO, status_code=201)
def solicitar_reserva(datos: CrearReservaDTO, servicio: ServicioReservas) -> ReservaDTO:
    return servicio.crear_reserva(datos)


@router.get("/{id_reserva}", response_model=ReservaDTO)
def consultar_reserva(id_reserva: UUID, servicio: ServicioReservas) -> ReservaDTO:
    try:
        return servicio.obtener_reserva(id_reserva)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


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
