"""Presentation layer exports for identidad_reputacion."""

from prestamos_recursos.contexts.identidad_reputacion.presentation.autenticacion_controller import (
    router as autenticacion_router,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.reputacion_controller import (
    router as reputacion_router,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.usuario_controller import (
    router as usuario_router,
)

__all__ = ["autenticacion_router", "reputacion_router", "usuario_router"]