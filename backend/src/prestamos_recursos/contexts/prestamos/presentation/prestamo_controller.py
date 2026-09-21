"""«Boundary» PrestamoController."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/prestamos", tags=["Préstamos"])


@router.post("/{id_prestamo}/devolucion")
def registrar_devolucion(id_prestamo: UUID):
    raise HTTPException(status_code=501, detail="Pendiente de implementar")


@router.get("/usuarios/{id_usuario}/historial")
def consultar_historial(id_usuario: UUID):
    raise HTTPException(status_code=501, detail="Pendiente de implementar")
