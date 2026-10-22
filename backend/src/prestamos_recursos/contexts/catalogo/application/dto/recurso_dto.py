from uuid import UUID

from pydantic import BaseModel

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


class CrearRecursoDTO(BaseModel):
    """DTO para la creación de un recurso en el catálogo."""

    nombre: str
    descripcion: str
    categoria: str
    marca: str
    modelo: str
    numero_serie: str
    color: str
    estado_fisico: str
    foto_url: str
