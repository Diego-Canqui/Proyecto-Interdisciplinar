from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.movimiento_reputacion import (
    MovimientoReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_movimiento_reputacion import (
    TipoMovimientoReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.movimiento_reputacion_repository import (
    MovimientoReputacionRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.movimiento_reputacion_model import (
    MovimientoReputacionModel,
)


class SqlMovimientoReputacionRepository(MovimientoReputacionRepository):
    """Implementación SQL append-only de MovimientoReputacionRepository (regla D13)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar(self, movimiento: MovimientoReputacion) -> None:
        """Registra un nuevo movimiento inmutable usando flush() sin commit() (D13)."""
        modelo = self._movimiento_a_modelo(movimiento)
        self._session.add(modelo)
        self._session.flush()

    def obtener_por_usuario(self, usuario_id: UUID) -> list[MovimientoReputacion]:
        """Retorna los movimientos del usuario ordenados del más reciente al más antiguo."""
        stmt = (
            select(MovimientoReputacionModel)
            .where(MovimientoReputacionModel.usuario_id == usuario_id)
            .order_by(
                MovimientoReputacionModel.fecha_movimiento.desc(),
                MovimientoReputacionModel.numero_secuencia.desc(),
            )
        )
        modelos = self._session.execute(stmt).scalars().all()
        return [self._modelo_a_movimiento(m) for m in modelos]

    def obtener_todos(self) -> list[MovimientoReputacion]:
        """Retorna todos los movimientos ordenados cronológicamente (más reciente primero)."""
        stmt = select(MovimientoReputacionModel).order_by(
            MovimientoReputacionModel.fecha_movimiento.desc(),
            MovimientoReputacionModel.numero_secuencia.desc(),
        )
        modelos = self._session.execute(stmt).scalars().all()
        return [self._modelo_a_movimiento(m) for m in modelos]

    def contar_por_usuario(self, usuario_id: UUID) -> int:
        """Retorna el total de movimientos persistidos para el usuario."""
        stmt = select(func.count(MovimientoReputacionModel.id)).where(
            MovimientoReputacionModel.usuario_id == usuario_id
        )
        return int(self._session.execute(stmt).scalar_one())

    def obtener_siguiente_secuencia(self, usuario_id: UUID) -> int:
        """Calcula el siguiente numero_secuencia determinista para el usuario."""
        stmt = select(func.max(MovimientoReputacionModel.numero_secuencia)).where(
            MovimientoReputacionModel.usuario_id == usuario_id
        )
        max_secuencia = self._session.execute(stmt).scalar_one()
        return (int(max_secuencia) + 1) if max_secuencia is not None else 1

    def _movimiento_a_modelo(
        self, movimiento: MovimientoReputacion
    ) -> MovimientoReputacionModel:
        """Convierte la entidad inmutable de dominio en modelo ORM."""
        return MovimientoReputacionModel(
            id=movimiento.id,
            usuario_id=movimiento.usuario_id,
            tipo=movimiento.tipo,
            motivo=movimiento.motivo,
            puntaje_anterior=movimiento.puntaje_anterior,
            variacion_puntos=movimiento.variacion_puntos,
            puntaje_resultante=movimiento.puntaje_resultante,
            fecha_movimiento=self._normalizar_fecha_utc(movimiento.fecha_movimiento),
            numero_secuencia=movimiento.numero_secuencia,
            sancion_id=movimiento.sancion_id,
            prestamo_id=movimiento.prestamo_id,
            reserva_id=movimiento.reserva_id,
            recurso_id=movimiento.recurso_id,
            recurso_nombre=movimiento.recurso_nombre,
        )

    def _modelo_a_movimiento(
        self, modelo: MovimientoReputacionModel
    ) -> MovimientoReputacion:
        """Reconstruye la entidad de dominio normalizando fecha_movimiento a UTC."""
        return MovimientoReputacion(
            id=modelo.id,
            usuario_id=modelo.usuario_id,
            tipo=TipoMovimientoReputacion(modelo.tipo),
            motivo=modelo.motivo,
            puntaje_anterior=modelo.puntaje_anterior,
            variacion_puntos=modelo.variacion_puntos,
            puntaje_resultante=modelo.puntaje_resultante,
            fecha_movimiento=self._normalizar_fecha_utc(modelo.fecha_movimiento),
            numero_secuencia=modelo.numero_secuencia,
            sancion_id=modelo.sancion_id,
            prestamo_id=modelo.prestamo_id,
            reserva_id=modelo.reserva_id,
            recurso_id=modelo.recurso_id,
            recurso_nombre=modelo.recurso_nombre,
        )

    @staticmethod
    def _normalizar_fecha_utc(fecha: datetime) -> datetime:
        """Garantiza datetime consciente en UTC (SQLite devuelve fechas naive)."""
        if fecha.tzinfo is None:
            return fecha.replace(tzinfo=UTC)
        return fecha.astimezone(UTC)
