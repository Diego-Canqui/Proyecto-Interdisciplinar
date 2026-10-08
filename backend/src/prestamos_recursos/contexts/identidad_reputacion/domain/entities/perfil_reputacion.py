from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import (
    PuntajeReputacion,
)
from prestamos_recursos.shared.base_entity import BaseEntity

if TYPE_CHECKING:
    from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
        ExcepcionAcademica,
    )
    from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion


@dataclass(kw_only=True)
class PerfilReputacion(BaseEntity):
    """«Aggregate Root» PerfilReputacion."""

    usuario_id: UUID
    puntaje: PuntajeReputacion
    nivel: NivelReputacion
    fecha_actualizacion: datetime
    sanciones: list[Sancion] = field(default_factory=list)

    def recalcular_nivel(self) -> NivelReputacion:
        """Recalcula el nivel según el puntaje actual y actualiza fecha_actualizacion."""
        puntos = self.puntaje.puntos

        if puntos <= 299:
            self.nivel = NivelReputacion.BAJO
        elif puntos <= 599:
            self.nivel = NivelReputacion.NORMAL
        elif puntos <= 799:
            self.nivel = NivelReputacion.BUENO
        else:
            self.nivel = NivelReputacion.EXCELENTE

        self.fecha_actualizacion = datetime.now(UTC)
        return self.nivel

    def aplicar_sancion(self, sancion: Sancion) -> None:
        """Añade la sanción, la aplica, descuenta puntos y recalcula el nivel."""
        self.sanciones.append(sancion)
        sancion.aplicar()
        # Restar puntos (puntos_descuento es negativo, así que restar un negativo = sumar)
        self.puntaje = self.puntaje.restar(abs(sancion.puntos_descuento))
        self.recalcular_nivel()

    def es_elegible_para_prestamo(
        self, excepciones_vigentes: list[ExcepcionAcademica] | None = None
    ) -> bool:
        """
        Determina si el usuario es elegible para préstamo.

        - False si nivel == BAJO
        - False si existe sanción activa=True Y no hay excepción vigente que la cubra
          (excepción vigente cubre TARDANZA e INASISTENCIA_RESERVA)
        - True en caso contrario
        """
        if excepciones_vigentes is None:
            excepciones_vigentes = []

        # Nivel BAJO -> no elegible
        if self.nivel == NivelReputacion.BAJO:
            return False

        # Verificar sanciones activas bloqueantes
        for sancion in self.sanciones:
            if not sancion.activa:
                continue

            # Verificar si hay alguna excepción vigente que cubra esta sanción
            cubre = False
            for excepcion in excepciones_vigentes:
                if excepcion.es_vigente() and self._excepcion_cubre_sancion(excepcion, sancion):
                    cubre = True
                    break

            if not cubre:
                return False

        return True

    def _excepcion_cubre_sancion(
        self, excepcion: ExcepcionAcademica, sancion: Sancion
    ) -> bool:
        """Verifica si la excepción cubre el tipo de sanción."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import (
            TipoSancion,
        )

        return sancion.tipo in (TipoSancion.TARDANZA, TipoSancion.INASISTENCIA_RESERVA)

    @classmethod
    def crear_para_usuario(cls, usuario_id: UUID) -> PerfilReputacion:
        """Factory: crea un perfil nuevo con puntaje 500 (NORMAL), sanciones vacías."""
        ahora = datetime.now(UTC)
        return cls(
            id=uuid4(),
            usuario_id=usuario_id,
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=ahora,
            sanciones=[],
        )