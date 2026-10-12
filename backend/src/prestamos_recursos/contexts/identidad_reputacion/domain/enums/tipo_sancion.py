from enum import Enum


class TipoSancion(str, Enum):
    """«enumeration» TipoSancion.

    Cada tipo define puntos_descuento, monto_descuento (deuda registrada) y la
    regla de duración de bloqueo (duracion_bloqueo).
    - TARDANZA: -10 pts, $0, gracia de 1 día y bloqueo 1:1 desde el 2º día de retraso
    - DANO_PARCIAL: -30 pts, $50, bloqueo 30 días
    - DANO_TOTAL: -100 pts, valor recurso (monto base 0, se calcula en service), bloqueo 60 días
    - INASISTENCIA_RESERVA: -15 pts, $0, bloqueo 3 días
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
        """Monto base en dólares registrado como deuda (el pago material es externo al sistema).

        Para DANO_TOTAL el valor real del recurso se calcula en el service.
        """
        mapping = {
            TipoSancion.TARDANZA: 0,
            TipoSancion.DANO_PARCIAL: 50,
            TipoSancion.DANO_TOTAL: 0,  # Se calcula en service según valor del recurso
            TipoSancion.INASISTENCIA_RESERVA: 0,
        }
        return mapping[self]

    def duracion_bloqueo(self, dias_retraso: int) -> int:
        """Días de bloqueo de la sanción según el tipo (de aquí se deriva fecha_fin).

        - TARDANZA (contrato: dias_retraso >= 1, validado antes con 422 — RF-07):
          gracia de 1 día: retraso 1 → 0 días (solo puntos) · retraso N >= 2 → N días.
          ValueError defensivo si dias_retraso < 1 (un usuario puntual no se
          sanciona por tardanza).
        - INASISTENCIA_RESERVA: 3 días · DANO_PARCIAL: 30 días · DANO_TOTAL: 60 días
          (duración fija: estos tipos ignoran dias_retraso, RF-07).
        """
        if self == TipoSancion.TARDANZA:
            if dias_retraso < 1:
                raise ValueError("TARDANZA exige dias_retraso >= 1")
            # Gracia de 1 día: retraso 1 → 0 días de bloqueo (solo descuenta puntos)
            if dias_retraso == 1:
                return 0
            # Bloqueo 1:1: un día de bloqueo por día de retraso desde el 2º día
            return dias_retraso

        mapping = {
            TipoSancion.INASISTENCIA_RESERVA: 3,
            TipoSancion.DANO_PARCIAL: 30,
            TipoSancion.DANO_TOTAL: 60,
        }
        return mapping[self]