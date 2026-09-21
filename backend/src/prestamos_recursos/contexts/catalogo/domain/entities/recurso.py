from __future__ import annotations

from dataclasses import dataclass

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.catalogo.domain.value_objects.ficha_tecnica import FichaTecnica
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Recurso(BaseEntity):
    """«Aggregate Root» Recurso."""

    nombre: str
    descripcion: str
    categoria: str
    estado: EstadoRecurso
    ficha_tecnica: FichaTecnica

    def marcar_disponible(self) -> None:
        raise NotImplementedError

    def marcar_no_disponible(self) -> None:
        raise NotImplementedError

    def actualizar_estado(self) -> None:
        raise NotImplementedError
