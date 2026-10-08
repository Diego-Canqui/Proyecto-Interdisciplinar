from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.excepcion_academica_repository import (
    ExcepcionAcademicaRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.excepcion_academica_model import (
    ExcepcionAcademicaModel,
)


class SqlExcepcionAcademicaRepository(ExcepcionAcademicaRepository):
    """Implementación SQL (SQLAlchemy) de ExcepcionAcademicaRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, excepcion_academica: ExcepcionAcademica) -> None:
        """
        Upsert de la excepción académica.

        - Si existe por ID, actualiza sus campos.
        - Si no existe, crea nueva.
        """
        stmt = select(ExcepcionAcademicaModel).where(
            ExcepcionAcademicaModel.id == excepcion_academica.id
        )
        modelo = self._session.execute(stmt).scalar_one_or_none()

        if modelo is None:
            # Crear nuevo
            modelo = self._excepcion_a_modelo(excepcion_academica)
            self._session.add(modelo)
        else:
            # Actualizar campos
            modelo.usuario_id = excepcion_academica.usuario_id
            modelo.motivo = excepcion_academica.motivo
            modelo.fecha_inicio = excepcion_academica.fecha_inicio
            modelo.fecha_fin = excepcion_academica.fecha_fin
            modelo.activa = excepcion_academica.activa

        self._session.flush()

    def obtener_por_id(self, id: UUID) -> ExcepcionAcademica | None:
        """Obtiene una excepción académica por su ID."""
        stmt = select(ExcepcionAcademicaModel).where(
            ExcepcionAcademicaModel.id == id
        )
        modelo = self._session.execute(stmt).scalar_one_or_none()
        if modelo is None:
            return None
        return self._modelo_a_excepcion(modelo)

    def obtener_vigentes_por_usuario(self, usuario_id: UUID) -> list[ExcepcionAcademica]:
        """
        Obtiene las excepciones académicas vigentes para un usuario.

        Filtros:
        - activa == True
        - fecha_inicio <= now <= fecha_fin
        """
        ahora = datetime.now(UTC)
        stmt = select(ExcepcionAcademicaModel).where(
            ExcepcionAcademicaModel.usuario_id == usuario_id,
            ExcepcionAcademicaModel.activa.is_(True),
            ExcepcionAcademicaModel.fecha_inicio <= ahora,
            ExcepcionAcademicaModel.fecha_fin >= ahora,
        )
        modelos = self._session.execute(stmt).scalars().all()
        return [self._modelo_a_excepcion(m) for m in modelos]

    def _excepcion_a_modelo(self, excepcion: ExcepcionAcademica) -> ExcepcionAcademicaModel:
        """Convierte entidad de dominio a modelo ORM."""
        return ExcepcionAcademicaModel(
            id=excepcion.id,
            usuario_id=excepcion.usuario_id,
            motivo=excepcion.motivo,
            fecha_inicio=excepcion.fecha_inicio,
            fecha_fin=excepcion.fecha_fin,
            activa=excepcion.activa,
        )

    def _modelo_a_excepcion(self, modelo: ExcepcionAcademicaModel) -> ExcepcionAcademica:
        """Convierte modelo ORM a entidad de dominio."""
        return ExcepcionAcademica(
            id=modelo.id,
            usuario_id=modelo.usuario_id,
            motivo=modelo.motivo,
            fecha_inicio=modelo.fecha_inicio,
            fecha_fin=modelo.fecha_fin,
            activa=modelo.activa,
        )