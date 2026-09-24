from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.catalogo.domain.entities import Recurso
from prestamos_recursos.contexts.catalogo.domain.enums import EstadoRecurso
from prestamos_recursos.contexts.catalogo.domain.repositories.recurso_repository import RecursoRepository
from prestamos_recursos.contexts.catalogo.domain.value_objects import FichaTecnica
from prestamos_recursos.contexts.catalogo.infrastructure.models import RecursoModel


class SqlRecursoRepository(RecursoRepository):
    """Implementación SQLAlchemy del repositorio de recursos."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, recurso: Recurso) -> None:
        model = self._session.get(RecursoModel, recurso.id)
        if model is None:
            model = RecursoModel(
                id=recurso.id,
                nombre=recurso.nombre,
                descripcion=recurso.descripcion,
                categoria=recurso.categoria,
                estado=recurso.estado,
                marca=recurso.ficha_tecnica.marca,
                modelo=recurso.ficha_tecnica.modelo,
                numero_serie=recurso.ficha_tecnica.numero_serie,
                color=recurso.ficha_tecnica.color,
                estado_fisico=recurso.ficha_tecnica.estado_fisico,
                foto_url=recurso.ficha_tecnica.foto_url,
            )
            self._session.add(model)
        else:
            model.nombre = recurso.nombre
            model.descripcion = recurso.descripcion
            model.categoria = recurso.categoria
            model.estado = recurso.estado
            model.marca = recurso.ficha_tecnica.marca
            model.modelo = recurso.ficha_tecnica.modelo
            model.numero_serie = recurso.ficha_tecnica.numero_serie
            model.color = recurso.ficha_tecnica.color
            model.estado_fisico = recurso.ficha_tecnica.estado_fisico
            model.foto_url = recurso.ficha_tecnica.foto_url
        self._session.flush()

    def obtener_por_id(self, id: UUID) -> Recurso | None:
        model = self._session.get(RecursoModel, id)
        if not model:
            return None
        return self._to_domain(model)

    def buscar_disponibles(self, categoria: str | None = None) -> list[Recurso]:
        stmt = select(RecursoModel).where(RecursoModel.estado == EstadoRecurso.DISPONIBLE)
        if categoria:
            stmt = stmt.where(RecursoModel.categoria == categoria)
        models = self._session.scalars(stmt).all()
        return [self._to_domain(m) for m in models]

    def actualizar_estado(self, id_recurso: UUID, estado: EstadoRecurso) -> None:
        model = self._session.get(RecursoModel, id_recurso)
        if model:
            model.estado = estado
            self._session.flush()

    @staticmethod
    def _to_domain(model: RecursoModel) -> Recurso:
        ficha = FichaTecnica(
            marca=model.marca,
            modelo=model.modelo,
            numero_serie=model.numero_serie,
            color=model.color,
            estado_fisico=model.estado_fisico,
            foto_url=model.foto_url,
        )
        return Recurso(
            id=model.id,
            nombre=model.nombre,
            descripcion=model.descripcion,
            categoria=model.categoria,
            estado=model.estado,
            ficha_tecnica=ficha,
        )
