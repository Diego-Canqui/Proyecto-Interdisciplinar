from uuid import UUID

from pydantic import BaseModel

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso


class RecursoDTO(BaseModel):
    """DTO RecursoDTO. TODO: ajustar los campos a lo que necesite el frontend."""

    id: UUID
    nombre: str
    descripcion: str
    categoria: str
    estado: EstadoRecurso
