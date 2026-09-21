from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.prestamos.application.dto.prestamo_dto import PrestamoDTO
from prestamos_recursos.contexts.prestamos.domain.repositories.checklist_repository import ChecklistRepository
from prestamos_recursos.contexts.prestamos.domain.repositories.garantia_repository import GarantiaRepository
from prestamos_recursos.contexts.prestamos.domain.repositories.prestamo_repository import PrestamoRepository


class PrestamoService:
    """«Service» PrestamoService."""

    def __init__(self, prestamo_repository: PrestamoRepository, checklist_repository: ChecklistRepository, garantia_repository: GarantiaRepository) -> None:
        self._prestamo_repository = prestamo_repository
        self._checklist_repository = checklist_repository
        self._garantia_repository = garantia_repository

    def solicitar_prestamo(self, id_usuario: UUID, id_recurso: UUID) -> bool:
        raise NotImplementedError

    def procesar_devolucion(self, id_prestamo: UUID) -> None:
        raise NotImplementedError

    def renovar_prestamo(self, id_prestamo: UUID) -> bool:
        raise NotImplementedError

    def validar_reglas_negocio(self) -> bool:
        raise NotImplementedError

    def consultar_historial(self, id_usuario: UUID) -> list[PrestamoDTO]:
        raise NotImplementedError
