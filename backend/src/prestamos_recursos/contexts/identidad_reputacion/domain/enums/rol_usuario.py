from enum import Enum


class RolUsuario(str, Enum):
    """«enumeration» RolUsuario.

    Valores DDD (5 roles):
    - ESTUDIANTE: rol por defecto en auto-registro
    - DOCENTE: personal docente
    - PERSONAL_ADMINISTRATIVO: personal administrativo
    - GESTOR_ALMACEN: gestor de almacén/recursos
    - ADMINISTRADOR_SISTEMA: administrador del sistema
    """

    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    PERSONAL_ADMINISTRATIVO = "PERSONAL_ADMINISTRATIVO"
    GESTOR_ALMACEN = "GESTOR_ALMACEN"
    ADMINISTRADOR_SISTEMA = "ADMINISTRADOR_SISTEMA"