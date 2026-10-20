from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import (
    PerfilReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion


class AplicarSancionDTO(BaseModel):
    """DTO para la petición de aplicar una sanción (POST /reputacion/sanciones)."""

    usuario_id: UUID
    tipo: TipoSancion
    motivo: str = Field(..., min_length=1, max_length=500)
    # Solo DANO_TOTAL: valor del recurso (RF-06); los demás tipos lo ignoran
    monto_opcional: Decimal | None = None
    # Solo TARDANZA: días de retraso, >= 1 (RF-07); los demás tipos lo ignoran
    dias_retardo: int | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def validar_premisas_por_tipo(self) -> Self:
        """RF-06/RF-07: cada tipo exige solo sus parámetros propios."""
        # Un usuario puntual nunca se sanciona por tardanza: exige dias_retardo >= 1
        if self.tipo == TipoSancion.TARDANZA and (self.dias_retardo is None or self.dias_retardo < 1):
            raise ValueError("TARDANZA exige dias_retardo >= 1")
        # La deuda de un recurso destruido no puede registrarse como $0
        if self.tipo == TipoSancion.DANO_TOTAL and (self.monto_opcional is None or self.monto_opcional <= 0):
            raise ValueError("DANO_TOTAL exige monto_opcional > 0")
        # Los demás tipos tienen duración y deuda fijas: ignoran ambos parámetros
        return self


class RegistrarExcepcionDTO(BaseModel):
    """DTO para la petición de registrar una excepción académica (POST /reputacion/excepciones)."""

    usuario_id: UUID
    motivo: str = Field(..., min_length=1, max_length=500)
    fecha_inicio: datetime
    fecha_fin: datetime

    model_config = {"from_attributes": True}


class SancionDTO(BaseModel):
    """DTO para representar una sanción en respuestas de API."""

    id: UUID
    tipo: TipoSancion
    puntos_descuento: int
    monto_descuento: Decimal
    motivo: str
    fecha_aplicacion: datetime
    fecha_fin: datetime  # RF-03: expuesta y devuelta en el historial
    activa: bool
    vigente: bool  # RF-02/RF-03: derivada de la entidad (activa y no expirada)

    @classmethod
    def from_entity(cls, sancion: Sancion) -> SancionDTO:
        """Crea un SancionDTO desde una entidad Sancion del dominio."""
        return cls(
            id=sancion.id,
            tipo=sancion.tipo,
            puntos_descuento=sancion.puntos_descuento,
            monto_descuento=sancion.monto_descuento,
            motivo=sancion.motivo,
            fecha_aplicacion=sancion.fecha_aplicacion,
            fecha_fin=sancion.fecha_fin,
            activa=sancion.activa,
            vigente=sancion.esta_vigente(),  # vigencia derivada de la entidad
        )

    model_config = {"from_attributes": True}


class ExcepcionAcademicaDTO(BaseModel):
    """DTO para representar una excepción académica en respuestas de API."""

    id: UUID
    usuario_id: UUID
    motivo: str
    fecha_inicio: datetime
    fecha_fin: datetime
    activa: bool

    @classmethod
    def from_entity(cls, excepcion: ExcepcionAcademica) -> ExcepcionAcademicaDTO:
        """Crea un ExcepcionAcademicaDTO desde una entidad ExcepcionAcademica del dominio."""
        return cls(
            id=excepcion.id,
            usuario_id=excepcion.usuario_id,
            motivo=excepcion.motivo,
            fecha_inicio=excepcion.fecha_inicio,
            fecha_fin=excepcion.fecha_fin,
            activa=excepcion.activa,
        )

    model_config = {"from_attributes": True}


class PerfilReputacionDTO(BaseModel):
    """DTO para representar el perfil de reputación completo en respuestas de API."""

    id: UUID
    usuario_id: UUID
    puntaje: int
    nivel: NivelReputacion
    fecha_actualizacion: datetime
    sanciones: list[SancionDTO]

    @classmethod
    def from_entity(cls, perfil: PerfilReputacion) -> PerfilReputacionDTO:
        """Crea un PerfilReputacionDTO desde una entidad PerfilReputacion del dominio."""
        return cls(
            id=perfil.id,
            usuario_id=perfil.usuario_id,
            puntaje=perfil.puntaje.puntos,
            nivel=perfil.nivel,
            fecha_actualizacion=perfil.fecha_actualizacion,
            sanciones=[SancionDTO.from_entity(s) for s in perfil.sanciones],
        )

    model_config = {"from_attributes": True}


class ElegibilidadDTO(BaseModel):
    """DTO para la respuesta de la consulta de la propia elegibilidad (RF-21).

    La razón (en lenguaje de negocio, con tipo y fecha de fin de la sanción
    bloqueante) solo se incluye si el usuario NO es elegible.
    """

    elegible: bool
    razon: str | None = None

    model_config = {"from_attributes": True}


class ResultadoAmnistiaDTO(BaseModel):
    """DTO para la respuesta de ejecutar la amnistía mensual (RF-13)."""

    perfiles_premiados: int  # 0 es un resultado válido: ningún perfil elegible

    model_config = {"from_attributes": True}