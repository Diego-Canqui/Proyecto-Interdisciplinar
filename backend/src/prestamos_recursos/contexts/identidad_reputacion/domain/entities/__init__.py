"""Entidades del dominio identidad_reputacion."""

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import (
    PerfilReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario

__all__ = [
    "ExcepcionAcademica",
    "PerfilReputacion",
    "Sancion",
    "Usuario",
]