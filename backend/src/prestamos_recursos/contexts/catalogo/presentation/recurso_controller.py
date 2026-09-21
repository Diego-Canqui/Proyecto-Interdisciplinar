"""«Boundary» RecursoController."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/recursos", tags=["Recursos"])


@router.get("")
def buscar_recursos(filtro: str = ""):
    raise HTTPException(status_code=501, detail="Pendiente de implementar")


@router.get("/{id_recurso}/disponibilidad")
def consultar_disponibilidad(id_recurso: UUID):
    raise HTTPException(status_code=501, detail="Pendiente de implementar")


@router.get("/{id_recurso}/ficha-tecnica")
def obtener_ficha_tecnica(id_recurso: UUID):
    raise HTTPException(status_code=501, detail="Pendiente de implementar")
