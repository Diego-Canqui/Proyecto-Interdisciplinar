"""«Boundary» PrestamoController."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import (
    RolUsuario,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    require_roles,
)
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
# DTOs para el ciclo de entrega física (garantía + checklist)
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


class EntregaCompletaDTO(BaseModel):
    """Datos completos para realizar la entrega y checklist en una sola operación."""

    tipo_garantia: TipoGarantia = TipoGarantia.CARNET_UNIVERSITARIO
    compromiso_contenido: str = Field(min_length=1)
    compromiso_firma_url: str = Field(min_length=1)
    compromiso_testigo: str = Field(min_length=1)
    observaciones_checklist: str = Field(min_length=1)
    fotos_urls: list[str] = Field(default_factory=list)


class DevolucionDTO(BaseModel):
    """Datos de recepción física e inspección de retorno."""

    observaciones: str = "Devuelto conforme"
    fotos_urls: list[str] = Field(default_factory=list)
    danos_detectados: bool = False


@router.post("/{id_prestamo}/entrega/iniciar")
def iniciar_entrega(
    id_prestamo: UUID,
    data: EntregaIniciarDTO,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    """Inicia el proceso de entrega creando garantía y checklist."""
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


@router.post("/{id_prestamo}/entrega/completar")
def completar_entrega(
    id_prestamo: UUID,
    data: EntregaCompletaDTO,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    """Ejecuta el ciclo de entrega completo (garantía + checklist) de forma unificada."""
    compromiso = CompromisoResponsabilidad(
        contenido=data.compromiso_contenido,
        fecha_firma=datetime.now(UTC),
        firma_url=data.compromiso_firma_url,
        testigo=data.compromiso_testigo,
    )
    try:
        service.completar_entrega(
            id_prestamo=id_prestamo,
            tipo_garantia=data.tipo_garantia,
            compromiso=compromiso,
            observaciones_checklist=data.observaciones_checklist,
            fotos_urls=data.fotos_urls,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) == "Préstamo no encontrado" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"detalle": "Entrega completada exitosamente", "estado": "ENTREGADO"}


@router.get("/{id_prestamo}/inspeccion")
def consultar_inspecciones(
    id_prestamo: UUID,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    """Consulta los datos de garantía y checklists (inicial y retorno)."""
    return service.consultar_inspecciones(id_prestamo)


# ------------------------------------------------------------
# Endpoint de devolución con checklist de recepción
# ------------------------------------------------------------

@router.post("/{id_prestamo}/devolucion")
def registrar_devolucion(
    id_prestamo: UUID,
    data: DevolucionDTO | None = None,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    """Registra la devolución con inspección de retorno y calcula retraso/sanción."""
    obs = data.observaciones if data else "Devuelto conforme"
    fotos = data.fotos_urls if data else []
    danos = data.danos_detectados if data else False
    try:
        dias_retraso = service.procesar_devolucion(
            id_prestamo=id_prestamo,
            observaciones_retorno=obs,
            fotos_urls=fotos,
            danos_detectados=danos,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) == "Préstamo no encontrado" else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {
        "detalle": "Devolución registrada",
        "estado": "DEVUELTO",
        "dias_retraso": dias_retraso,
    }


@router.post("/{id_prestamo}/renovar")
def renovar_prestamo(
    id_prestamo: UUID,
    service: PrestamoService = Depends(get_prestamo_service),
) -> dict:
    """Renueva un préstamo activo extendiendo el plazo de devolución."""
    try:
        service.renovar_prestamo(id_prestamo)
    except ValueError as exc:
        status_code = 404 if str(exc) == "Préstamo no encontrado" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"detalle": "Préstamo renovado exitosamente por 7 días"}


@router.get("/usuarios/{id_usuario}/historial", response_model=list[PrestamoDTO])
def consultar_historial(
    id_usuario: UUID,
    service: PrestamoService = Depends(get_prestamo_service),
) -> list[PrestamoDTO]:
    """Consulta el historial de préstamos de un usuario."""
    return service.consultar_historial(id_usuario)


@router.get("", response_model=list[PrestamoDTO])
def listar_todos(
    _usuario: UsuarioDTO = Depends(  # noqa: B008
        require_roles(RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN)  # noqa: B008
    ),
    service: PrestamoService = Depends(get_prestamo_service),  # noqa: B008
) -> list[PrestamoDTO]:
    """Lista todos los préstamos registrados (solo para roles de gestión)."""
    return service.consultar_todos()
