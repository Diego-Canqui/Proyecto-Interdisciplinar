from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from prestamos_recursos.contexts.catalogo.application.dto.recurso_dto import RecursoDTO
from prestamos_recursos.contexts.catalogo.domain.entities import Recurso
from prestamos_recursos.contexts.catalogo.domain.enums import EstadoRecurso
from prestamos_recursos.contexts.catalogo.domain.repositories.recurso_repository import (
    RecursoRepository,
)
from prestamos_recursos.contexts.catalogo.domain.value_objects import FichaTecnica


class RecursoApplicationService:
    """Servicio de aplicación para la gestión de recursos del catálogo."""

    def __init__(self, recurso_repository: RecursoRepository) -> None:
        self._recurso_repository = recurso_repository

    def crear_recurso(
        self,
        nombre: str,
        descripcion: str,
        categoria: str,
        marca: str | None = None,
        modelo: str | None = None,
        numero_serie: str | None = None,
        color: str | None = None,
        estado_fisico: str = "",
        foto_url: str = "",
        especificaciones: dict[str, Any] | None = None,
    ) -> UUID:
        ficha = FichaTecnica(
            marca=marca,
            modelo=modelo,
            numero_serie=numero_serie,
            color=color,
            estado_fisico=estado_fisico,
            foto_url=foto_url,
            especificaciones=dict(especificaciones or {}),
        )
        if not ficha.es_valida():
            raise ValueError("La ficha técnica proporcionada no es válida.")

        recurso = Recurso(
            id=uuid4(),
            nombre=nombre,
            descripcion=descripcion,
            categoria=categoria,
            estado=EstadoRecurso.DISPONIBLE,
            ficha_tecnica=ficha,
        )
        self._recurso_repository.guardar(recurso)
        return recurso.id

    def obtener_por_id(self, id_recurso: UUID) -> RecursoDTO | None:
        recurso = self._recurso_repository.obtener_por_id(id_recurso)
        if not recurso:
            return None
        return self._to_dto(recurso)

    def buscar(self, filtro: str = "") -> list[RecursoDTO]:
        recursos = self._recurso_repository.buscar(filtro)
        return [self._to_dto(r) for r in recursos]

    def buscar_disponibles(self, categoria: str | None = None) -> list[RecursoDTO]:
        recursos = self._recurso_repository.buscar_disponibles(categoria or "")
        return [self._to_dto(r) for r in recursos]

    def actualizar_recurso(
        self,
        id_recurso: UUID,
        nombre: str,
        descripcion: str,
        categoria: str,
        marca: str | None = None,
        modelo: str | None = None,
        numero_serie: str | None = None,
        color: str | None = None,
        estado_fisico: str = "",
        foto_url: str = "",
        especificaciones: dict[str, Any] | None = None,
    ) -> RecursoDTO:
        recurso = self._recurso_repository.obtener_por_id(id_recurso)
        if not recurso:
            raise ValueError(f"Recurso con id {id_recurso} no encontrado.")
        ficha = FichaTecnica(
            marca=marca,
            modelo=modelo,
            numero_serie=numero_serie,
            color=color,
            estado_fisico=estado_fisico,
            foto_url=foto_url,
            especificaciones=dict(especificaciones or {}),
        )
        if not ficha.es_valida():
            raise ValueError("La ficha técnica proporcionada no es válida.")
        recurso.nombre = nombre
        recurso.descripcion = descripcion
        recurso.categoria = categoria
        recurso.ficha_tecnica = ficha
        self._recurso_repository.guardar(recurso)
        return self._to_dto(recurso)

    def actualizar_estado(self, id_recurso: UUID, nuevo_estado: EstadoRecurso) -> None:
        recurso = self._recurso_repository.obtener_por_id(id_recurso)
        if not recurso:
            raise ValueError(f"Recurso con id {id_recurso} no encontrado.")
        recurso.actualizar_estado(nuevo_estado)
        self._recurso_repository.guardar(recurso)

    def consultar_disponibilidad(self, id_recurso: UUID) -> bool:
        recurso = self._recurso_repository.obtener_por_id(id_recurso)
        if not recurso:
            return False
        return recurso.estado == EstadoRecurso.DISPONIBLE

    def obtener_ficha_tecnica(self, id_recurso: UUID) -> RecursoDTO | None:
        return self.obtener_por_id(id_recurso)

    @staticmethod
    def _to_dto(recurso: Recurso) -> RecursoDTO:
        ficha = recurso.ficha_tecnica
        return RecursoDTO(
            id=recurso.id,
            nombre=recurso.nombre,
            descripcion=recurso.descripcion,
            categoria=recurso.categoria,
            estado=recurso.estado,
            marca=ficha.marca,
            modelo=ficha.modelo,
            numero_serie=ficha.numero_serie,
            color=ficha.color,
            estado_fisico=ficha.estado_fisico,
            foto_url=ficha.foto_url,
            especificaciones=dict(ficha.especificaciones),
        )


RecursoService = RecursoApplicationService
