from enum import Enum


class TipoSancion(str, Enum):
    """«enumeration» TipoSancion.

    Cada tipo define puntos_descuento y monto_descuento base.
    - TARDANZA: -10 pts, $0
    - DANO_PARCIAL: -30 pts, $50
    - DANO_TOTAL: -100 pts, valor recurso (monto base 0, se calcula en service)
    - INASISTENCIA_RESERVA: -15 pts, $0
    """

    TARDANZA = "TARDANZA"
    DANO_PARCIAL = "DANO_PARCIAL"
    DANO_TOTAL = "DANO_TOTAL"
    INASISTENCIA_RESERVA = "INASISTENCIA_RESERVA"

    @property
    def puntos_descuento(self) -> int:
        """Puntos que se descuentan al aplicar esta sanción (siempre negativo)."""
        mapping = {
            TipoSancion.TARDANZA: -10,
            TipoSancion.DANO_PARCIAL: -30,
            TipoSancion.DANO_TOTAL: -100,
            TipoSancion.INASISTENCIA_RESERVA: -15,
        }
        return mapping[self]

    @property
    def monto_descuento(self) -> int:
        """Monto base en dólares que se cobra (0 si no hay cobro automático).

        Para DANO_TOTAL el valor real del recurso se calcula en el service.
        """
        mapping = {
            TipoSancion.TARDANZA: 0,
            TipoSancion.DANO_PARCIAL: 50,
            TipoSancion.DANO_TOTAL: 0,  # Se calcula en service según valor del recurso
            TipoSancion.INASISTENCIA_RESERVA: 0,
        }
        return mapping[self]