from __future__ import annotations

from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.excepcion_academica_repository import ExcepcionAcademicaRepository
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.perfil_reputacion_repository import PerfilReputacionRepository
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.sancion_repository import SancionRepository


class ReputacionService:
    """«Service» ReputacionService."""

    def __init__(self, perfil_reputacion_repository: PerfilReputacionRepository, sancion_repository: SancionRepository, excepcion_academica_repository: ExcepcionAcademicaRepository) -> None:
        self._perfil_reputacion_repository = perfil_reputacion_repository
        self._sancion_repository = sancion_repository
        self._excepcion_academica_repository = excepcion_academica_repository

    def aplicar_sancion(self, id_usuario: UUID, tipo: TipoSancion) -> None:
        raise NotImplementedError
