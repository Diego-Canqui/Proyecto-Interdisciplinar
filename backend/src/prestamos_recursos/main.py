from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from prestamos_recursos.config import settings
from prestamos_recursos.contexts.catalogo.presentation.recurso_controller import (
    router as recurso_router,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.autenticacion_controller import (
    router as autenticacion_router,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.reputacion_controller import (
    router as reputacion_router,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.usuario_controller import (
    router as usuario_router,
)
from prestamos_recursos.contexts.prestamos.presentation.prestamo_controller import (
    router as prestamo_router,
)
from prestamos_recursos.contexts.reservas.presentation.reserva_controller import (
    router as reserva_router,
)
from prestamos_recursos.shared.database import Base, engine
from prestamos_recursos.shared.rate_limit import limiter

app = FastAPI(title="Proyecto Interdisciplinar - Préstamo de Recursos")

# CORS configurado desde settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def crear_tablas() -> None:
    # Provisional: sin Alembic todavía, se crean las tablas directo desde los modelos.
    Base.metadata.create_all(bind=engine)


app.include_router(autenticacion_router)
app.include_router(usuario_router)
app.include_router(reputacion_router)
app.include_router(recurso_router)
app.include_router(reserva_router)
app.include_router(prestamo_router)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}
