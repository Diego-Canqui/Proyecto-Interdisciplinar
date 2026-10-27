"""«Boundary» PrestamoController."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from prestamos_recursos.contexts.prestamos.application.dto.prestamo_dto import PrestamoDTO
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.domain.value_objects.compromiso_responsabilidad import (
    CompromisoResponsabilidad,
)
from prestamos_recursos.contexts.prestamos.presentation.dependencies import (
    get_prestamo_service,
)

router = APIRouter(prefix="/prestamos", tags=["Préstamos"])


# ------------------------------------------------------------
# DTO y endpoint para iniciar la entrega (garantía + checklist)
# ------------------------------------------------------------

class EntregaIniciarDTO(BaseModel):
    """Datos necesarios para iniciar la entrega de un préstamo."""

    tipo_garantia: TipoGarantia
    compromiso_contenido: str = Field(min_length=1)
    compromiso_firma_url: str = Field(min_length=1)
    compromiso_testigo: str = Field(min_length=1)


class ChecklistItemDTO(BaseModel):
    observaciones: str = ""
    fotos_urls: list[str] = Field(default_factory=list)


@router.post("/{id_prestamo}/entrega/iniciar")
def iniciar_entrega(
    id_prestamo: UUID,
    data: EntregaIniciarDTO,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    """Inicia el proceso de entrega creando garantía y checklist.

    Responde con ``{"detalle": "Entrega iniciada"}``.
    """
    compromiso = CompromisoResponsabilidad(
        contenido=data.compromiso_contenido,
        fecha_firma=datetime.now(UTC),
        firma_url=data.compromiso_firma_url,
        testigo=data.compromiso_testigo,
    )
    try:
        service.iniciar_entrega(id_prestamo, data.tipo_garantia, compromiso)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Préstamo no encontrado" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"detalle": "Entrega iniciada"}


@router.post("/{id_prestamo}/entrega/checklist/items")
def agregar_item_checklist(
    id_prestamo: UUID,
    data: ChecklistItemDTO,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    try:
        service.agregar_item_checklist(id_prestamo, data.observaciones, data.fotos_urls)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Préstamo no encontrado" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"detalle": "Ítem agregado al checklist"}


@router.post("/{id_prestamo}/entrega/confirmar")
def confirmar_entrega(
    id_prestamo: UUID,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    try:
        service.confirmar_entrega(id_prestamo)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Préstamo no encontrado" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"detalle": "Entrega confirmada"}


@router.post("/{id_prestamo}/entrega/finalizar")
def finalizar_entrega(
    id_prestamo: UUID,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    try:
        service.finalizar_entrega(id_prestamo)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Préstamo no encontrado" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"detalle": "Entrega finalizada", "estado": "ENTREGADO"}

# ------------------------------------------------------------
# Endpoint de devolución (placeholder - sigue pendiente)
# ------------------------------------------------------------



@router.post("/{id_prestamo}/devolucion")
def registrar_devolucion(
    id_prestamo: UUID,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    """Registra la devolución del préstamo y devuelve los días de retraso."""
    try:
        dias_retraso = service.procesar_devolucion(id_prestamo)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Préstamo no encontrado" else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {
        "detalle": "Devolución registrada",
        "estado": "DEVUELTO",
        "dias_retraso": dias_retraso,
    }


@router.get("/usuarios/{id_usuario}/historial", response_model=list[PrestamoDTO])
def consultar_historial(
    id_usuario: UUID,
    service: PrestamoService = Depends(get_prestamo_service),
) -> list[PrestamoDTO]:
    """Consulta el historial de préstamos de un usuario."""
    return service.consultar_historial(id_usuario)

