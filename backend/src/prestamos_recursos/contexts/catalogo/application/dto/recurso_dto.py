from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso


class RecursoDTO(BaseModel):
    """DTO RecursoDTO con detalles del recurso y ficha técnica."""

    id: UUID
    nombre: str
    descripcion: str
    categoria: str
    estado: EstadoRecurso
    marca: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    color: str | None = None
    estado_fisico: str | None = None
    foto_url: str | None = None
    especificaciones: dict[str, Any] = Field(default_factory=dict)
    disponible_desde: datetime | None = None


class CrearRecursoDTO(BaseModel):
    """DTO para la creación de un recurso en el catálogo."""

    nombre: str
    descripcion: str
    categoria: str
    marca: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    color: str | None = None
    estado_fisico: str
    foto_url: str
    especificaciones: dict[str, Any] = Field(default_factory=dict)


class ActualizarEstadoRecursoDTO(BaseModel):
    """DTO para actualizar el estado de un recurso."""

    estado: EstadoRecurso


class ActualizarRecursoDTO(BaseModel):
    """DTO para actualizar los datos y ficha técnica de un recurso."""

    nombre: str
    descripcion: str
    categoria: str
    marca: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    color: str | None = None
    estado_fisico: str
    foto_url: str
    especificaciones: dict[str, Any] = Field(default_factory=dict)
