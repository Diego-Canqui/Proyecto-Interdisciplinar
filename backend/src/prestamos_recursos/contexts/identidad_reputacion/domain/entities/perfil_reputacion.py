from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion
from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class PerfilReputacion(BaseEntity):
    """«Aggregate Root» PerfilReputacion."""

    usuario_id: UUID
    puntaje: PuntajeReputacion
    nivel: NivelReputacion
    fecha_actualizacion: datetime

    def recalcular_nivel(self) -> None:
        raise NotImplementedError

    def aplicar_sancion(self) -> None:
        raise NotImplementedError

    def es_elegible_para_prestamo(self) -> bool:
        raise NotImplementedError
