"""«Boundary» PrestamoController."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from prestamos_recursos.contexts.prestamos.application.dto.prestamo_dto import PrestamoDTO
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.presentation.dependencies import get_prestamo_service

router = APIRouter(prefix="/prestamos", tags=["Préstamos"])


@router.post("/{id_prestamo}/devolucion")
def registrar_devolucion(id_prestamo: UUID):
        service.procesar_devolucion(id_prestamo)
    return {"detalle": "Devolución procesada"}


@router.get("/usuarios/{id_usuario}/historial", response_model=list[PrestamoDTO])
def consultar_historial(
    id_usuario: UUID,
    service: PrestamoService = Depends(get_prestamo_service),
) -> list[PrestamoDTO]:
    """Consulta el historial de préstamos de un usuario."""
    return service.consultar_historial(id_usuario)

