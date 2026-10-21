"""Dependencias para la API de préstamos."""

from fastapi import Depends
from sqlalchemy.orm import Session

# Servicios y repositorios de reputación
from prestamos_recursos.contexts.identidad_reputacion.application.reputacion_service import (
    ReputacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_excepcion_academica_repository import (
    SqlExcepcionAcademicaRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_perfil_reputacion_repository import (
    SqlPerfilReputacionRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.repositories.sql_usuario_repository import (
    SqlUsuarioRepository,
)
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_checklist_repository import (
    SqlChecklistRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_garantia_repository import (
    SqlGarantiaRepository,
)

# Repositorios de préstamos
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_prestamo_repository import (
    SqlPrestamoRepository,
)
from prestamos_recursos.shared.database import get_session


def get_prestamo_service(session: Session = Depends(get_session)) -> PrestamoService:
    """Factory para inyectar `PrestamoService` con sus dependencias reales."""
    reputacion_service = ReputacionService(
        perfil_reputacion_repository=SqlPerfilReputacionRepository(session),
        excepcion_academica_repository=SqlExcepcionAcademicaRepository(session),
        usuario_repository=SqlUsuarioRepository(session),
    )
    return PrestamoService(
        prestamo_repository=SqlPrestamoRepository(session),
        checklist_repository=SqlChecklistRepository(session),
        garantia_repository=SqlGarantiaRepository(session),
        reputacion_service=reputacion_service,
    )
