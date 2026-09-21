"""«Boundary» AutenticacionController."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login")
def login(credenciales: dict):
    raise HTTPException(status_code=501, detail="Pendiente de implementar")


@router.post("/logout")
def logout(token: str):
    raise HTTPException(status_code=501, detail="Pendiente de implementar")


@router.get("/perfil")
def obtener_perfil():
    raise HTTPException(status_code=501, detail="Pendiente de implementar")
