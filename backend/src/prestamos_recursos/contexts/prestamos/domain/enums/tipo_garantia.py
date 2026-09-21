from enum import Enum


class TipoGarantia(str, Enum):
    """«enumeration» TipoGarantia."""

    DOCUMENTO_IDENTIDAD = "DOCUMENTO_IDENTIDAD"
    CARNET_UNIVERSITARIO = "CARNET_UNIVERSITARIO"
    DEPOSITO_ECONOMICO = "DEPOSITO_ECONOMICO"
    OTRO = "OTRO"
