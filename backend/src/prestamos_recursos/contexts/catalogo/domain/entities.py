from __future__ import annotations

from dataclasses import dataclass

from prestamos_recursos.contexts.catalogo.domain.enums import EstadoRecurso
from prestamos_recursos.contexts.catalogo.domain.value_objects import FichaTecnica
from prestamos_recursos.shared.base_entity import BaseEntity


@dataclass(kw_only=True)
class Recurso(BaseEntity):
    """Aggregate Root que representa un recurso en el catálogo."""

    nombre: str
    descripcion: str
    categoria: str
    estado: EstadoRecurso
    ficha_tecnica: FichaTecnica

    def marcar_disponible(self) -> None:
        """Marca el recurso como disponible si cumple con las condiciones."""
        if self.estado == EstadoRecurso.FUERA_DE_SERVICIO:
            raise ValueError("No se puede marcar como disponible un recurso fuera de servicio.")
        self.estado = EstadoRecurso.DISPONIBLE

    def marcar_no_disponible(self) -> None:
        """Marca el recurso como en uso o no disponible."""
        self.estado = EstadoRecurso.EN_USO

    def actualizar_estado(self, nuevo_estado: EstadoRecurso) -> None:
        """Actualiza el estado del recurso con validación de dominio."""
        if not isinstance(nuevo_estado, EstadoRecurso):
            raise TypeError("El estado debe ser una instancia de EstadoRecurso.")
        self.estado = nuevo_estado
