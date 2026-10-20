"""Excepciones de aplicación del contexto identidad_reputacion (RF-23).

Son excepciones propias, **sin HTTP**: el contexto `prestamos` las captura
directamente (llamadas inter-contexto al servicio) y el controller las traduce
al código HTTP correspondiente.
"""


class UsuarioNoEncontrado(Exception):
    """El «usuario_id» indicado no corresponde a ningún usuario registrado (RF-23)."""


class SancionInvalida(Exception):
    """Premisas inválidas al aplicar una sanción (RF-06/RF-07)."""


class ExcepcionNoEncontrada(Exception):
    """La excepción académica solicitada no existe (RF-22)."""
