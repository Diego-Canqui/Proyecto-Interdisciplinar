"""«Boundary» ReservaController."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/reservas", tags=["Reservas"])


@router.post("")
def solicitar_reserva(id_usuario: UUID, id_recurso: UUID):
    raise HTTPException(status_code=501, detail="Pendiente de implementar")
