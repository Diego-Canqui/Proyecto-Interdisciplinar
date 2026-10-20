"""Dependencias para la API de préstamos."""

from fastapi import Depends
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_checklist_repository import (
    SqlChecklistRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_garantia_repository import (
    SqlGarantiaRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_prestamo_repository import (
    SqlPrestamoRepository,
)
from prestamos_recursos.shared.database import get_session


def get_prestamo_service(
    session: Session = Depends(get_session),
) -> PrestamoService:
    """Factory para inyectar PrestamoService con repositorios SQL reales."""
    return PrestamoService(
        prestamo_repository=SqlPrestamoRepository(session),
        checklist_repository=SqlChecklistRepository(session),
        garantia_repository=SqlGarantiaRepository(session),
    )

