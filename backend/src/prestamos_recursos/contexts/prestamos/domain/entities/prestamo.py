from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.shared.base_entity import BaseEntity


def _ensure_utc(dt: datetime) -> datetime:
    """Asegura que un datetime tenga zona horaria UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@dataclass(kw_only=True)
class Prestamo(BaseEntity):
    """«Aggregate Root» Prestamo."""

    reserva_id: UUID
    recurso_id: UUID
    usuario_id: UUID
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: EstadoPrestamo
    fecha_entrega_real: datetime | None = None
    fecha_devolucion_real: datetime | None = None

    def __post_init__(self) -> None:
        inicio = _ensure_utc(self.fecha_inicio)
        fin = _ensure_utc(self.fecha_fin)
        if fin <= inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")

    def iniciar(self) -> None:
        """Inicia el préstamo marcándolo como POR_ENTREGAR si es válido."""
        if self.estado in (EstadoPrestamo.DEVUELTO, EstadoPrestamo.CANCELADO):
            raise ValueError(f"No se puede iniciar un préstamo en estado {self.estado.value}")
        self.estado = EstadoPrestamo.POR_ENTREGAR

    def marcar_entregado(self, fecha_entrega: datetime | None = None) -> None:
        """Marca el préstamo como entregado al usuario tras confirmar la inspección."""
        if self.estado != EstadoPrestamo.POR_ENTREGAR:
            raise ValueError(
                "Sólo pueden marcarse como entregados préstamos pendientes de entrega (POR_ENTREGAR)"
            )
        self.estado = EstadoPrestamo.ENTREGADO
        self.fecha_entrega_real = (
            _ensure_utc(fecha_entrega) if fecha_entrega is not None else datetime.now(UTC)
        )

    def limite_recogida(self) -> datetime:
        """Retorna el límite máximo para recoger físicamente el recurso en ventanilla."""
        return min(_ensure_utc(self.fecha_inicio) + timedelta(minutes=30), _ensure_utc(self.fecha_fin))

    def calcular_dias_retraso(self, fecha_referencia: datetime | None = None) -> int:
        """Calcula cuántos días de retraso hay respecto a fecha_fin."""
        fecha = _ensure_utc(fecha_referencia) if fecha_referencia is not None else datetime.now(UTC)
        fin = _ensure_utc(self.fecha_fin)
        dias = (fecha.date() - fin.date()).days
        return max(0, dias)

    def es_devolucion_puntual(self, fecha_referencia: datetime | None = None) -> bool:
        """Indica si la devolución ocurre en o antes de la fecha y hora límite pactadas."""
        referencia = (
            fecha_referencia
            if fecha_referencia is not None
            else (self.fecha_devolucion_real or datetime.now(UTC))
        )
        return _ensure_utc(referencia) <= _ensure_utc(self.fecha_fin)

    def devolver(self, fecha_devolucion: datetime | None = None) -> int:
        """
        Procesa la devolución del préstamo.
        Solo se puede devolver si está ENTREGADO o VENCIDO.
        Retorna los días de retraso (0 si fue a tiempo o anticipado).
        """
        if self.estado == EstadoPrestamo.DEVUELTO:
            raise ValueError("El préstamo ya fue devuelto")
        if self.estado == EstadoPrestamo.CANCELADO:
            raise ValueError("No se puede devolver un préstamo cancelado")
        if self.estado == EstadoPrestamo.POR_ENTREGAR:
            raise ValueError(
                "No se puede devolver un préstamo pendiente de entrega física (POR_ENTREGAR)"
            )

        fecha = _ensure_utc(fecha_devolucion) if fecha_devolucion is not None else datetime.now(UTC)
        dias_retraso = self.calcular_dias_retraso(fecha)
        self.estado = EstadoPrestamo.DEVUELTO
        self.fecha_devolucion_real = fecha
        return dias_retraso

    def vencer(self, fecha_actual: datetime | None = None) -> None:
        """Marca el préstamo como VENCIDO solo si está ENTREGADO y superó fecha_fin."""
        if self.estado != EstadoPrestamo.ENTREGADO:
            raise ValueError(
                f"No se puede marcar como vencido un préstamo en estado {self.estado.value}"
            )

        fecha = _ensure_utc(fecha_actual) if fecha_actual is not None else datetime.now(UTC)
        fin = _ensure_utc(self.fecha_fin)
        if fecha <= fin:
            raise ValueError("El préstamo aún no ha superado su fecha de finalización")

        self.estado = EstadoPrestamo.VENCIDO

    def cancelar(self, motivo: str = "") -> None:
        """Cancela administrativamente el préstamo si está pendiente de entrega física (POR_ENTREGAR)."""
        if self.estado == EstadoPrestamo.DEVUELTO:
            raise ValueError("No se puede cancelar un préstamo que ya ha sido devuelto")
        if self.estado != EstadoPrestamo.POR_ENTREGAR:
            raise ValueError(
                "Solo se pueden cancelar préstamos pendientes de entrega física (POR_ENTREGAR)"
            )
        self.estado = EstadoPrestamo.CANCELADO
