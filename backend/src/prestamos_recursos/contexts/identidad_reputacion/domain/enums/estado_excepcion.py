from enum import Enum


class EstadoExcepcion(str, Enum):
    """«enumeration» EstadoExcepcion.

    Estado de presentación de una excepción académica en la ficha de gestión (RF-04):
    - VIGENTE: activa y dentro de su rango de fechas (inclusivo, RF-14 de la 002)
    - PROGRAMADA: activa y aún no ha empezado
    - VENCIDA: activa y ya terminó
    - ANULADA: registrada por error (activa=False)
    """

    VIGENTE = "VIGENTE"
    PROGRAMADA = "PROGRAMADA"
    VENCIDA = "VENCIDA"
    ANULADA = "ANULADA"
