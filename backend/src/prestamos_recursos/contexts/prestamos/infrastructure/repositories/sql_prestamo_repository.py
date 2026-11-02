from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.domain.repositories.prestamo_repository import (
    PrestamoRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.models.prestamo_model import PrestamoModel


class SqlPrestamoRepository(PrestamoRepository):
    """Implementación SQL (SQLAlchemy) de PrestamoRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, modelo: PrestamoModel) -> Prestamo:
        return Prestamo(
            id=modelo.id,
            reserva_id=modelo.reserva_id,
            recurso_id=modelo.recurso_id,
            usuario_id=modelo.usuario_id,
            fecha_inicio=modelo.fecha_inicio,
            fecha_fin=modelo.fecha_fin,
            estado=EstadoPrestamo(modelo.estado),
        )

    def guardar(self, prestamo: Prestamo) -> None:
        modelo = self._session.get(PrestamoModel, prestamo.id)
        if modelo is None:
            modelo = PrestamoModel(id=prestamo.id)
            self._session.add(modelo)

        modelo.reserva_id = prestamo.reserva_id
        modelo.recurso_id = prestamo.recurso_id
        modelo.usuario_id = prestamo.usuario_id
        modelo.fecha_inicio = prestamo.fecha_inicio
        modelo.fecha_fin = prestamo.fecha_fin
        modelo.estado = prestamo.estado

    def obtener_por_id(self, id: UUID) -> Prestamo | None:
        modelo = self._session.get(PrestamoModel, id)
        if modelo is None:
            return None
        return self._to_entity(modelo)

    def obtener_activos(self) -> list[Prestamo]:
        modelos = (
            self._session.scalars(
                select(PrestamoModel).where(PrestamoModel.estado == EstadoPrestamo.ACTIVO)
            )
            .all()
        )
        return [self._to_entity(m) for m in modelos]

    def obtener_por_usuario(self, id_usuario: UUID) -> list[Prestamo]:
        modelos = (
            self._session.scalars(
                select(PrestamoModel).where(PrestamoModel.usuario_id == id_usuario)
            )
            .all()
        )
        return [self._to_entity(m) for m in modelos]

    def obtener_todos(self) -> list[Prestamo]:
        modelos = (
            self._session.scalars(
                select(PrestamoModel).order_by(
                    PrestamoModel.fecha_inicio.desc(), PrestamoModel.id
                )
            )
            .all()
        )
        return [self._to_entity(m) for m in modelos]


