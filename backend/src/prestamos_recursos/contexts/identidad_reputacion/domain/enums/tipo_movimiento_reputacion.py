from enum import Enum


class TipoMovimientoReputacion(str, Enum):
    """Tipos de evento registrados en la bitácora inmutable de reputación."""

    BONIFICACION_ENTREGA_PUNTUAL = "BONIFICACION_ENTREGA_PUNTUAL"
    BONIFICACION_DEVOLUCION_PUNTUAL = "BONIFICACION_DEVOLUCION_PUNTUAL"
    SANCION = "SANCION"
    AMNISTIA_MENSUAL = "AMNISTIA_MENSUAL"
    SALDO_INICIAL_HEREDADO = "SALDO_INICIAL_HEREDADO"
