from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prestamos_recursos.contexts.identidad_reputacion.presentation.autenticacion_controller import router as autenticacion_router
from prestamos_recursos.contexts.catalogo.presentation.recurso_controller import router as recurso_router
from prestamos_recursos.contexts.reservas.presentation.reserva_controller import router as reserva_router
from prestamos_recursos.contexts.prestamos.presentation.prestamo_controller import router as prestamo_router

app = FastAPI(title="Proyecto Interdisciplinar - Préstamo de Recursos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend en desarrollo (Vite)
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(autenticacion_router)
app.include_router(recurso_router)
app.include_router(reserva_router)
app.include_router(prestamo_router)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
