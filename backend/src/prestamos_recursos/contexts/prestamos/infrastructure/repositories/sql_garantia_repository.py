from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.domain.entities.garantia import Garantia
from prestamos_recursos.contexts.prestamos.domain.repositories.garantia_repository import GarantiaRepository
from prestamos_recursos.contexts.prestamos.infrastructure.models.garantia_model import GarantiaModel


class SqlGarantiaRepository(GarantiaRepository):
    """Implementación SQL (SQLAlchemy) de GarantiaRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, modelo: GarantiaModel) -> Garantia:
        # NOTE: ``compromiso`` is a value object; here we store only its textual content.
        return Garantia(
            id=modelo.id,
            prestamo_id=modelo.prestamo_id,
            tipo=modelo.tipo,
            estado=modelo.estado,
            fecha_registro=modelo.fecha_registro,
            fecha_liberacion=modelo.fecha_liberacion,
            compromiso=modelo.compromiso_contenido,  # simple string mapping
        )

    def _to_model(self, garantia: Garantia) -> GarantiaModel:
        modelo = self._session.get(GarantiaModel, garantia.id)
        if modelo is None:
            modelo = GarantiaModel(id=garantia.id)
            self._session.add(modelo)
        modelo.prestamo_id = garantia.prestamo_id
        modelo.tipo = garantia.tipo
        modelo.estado = garantia.estado
        modelo.fecha_registro = garantia.fecha_registro
        modelo.fecha_liberacion = garantia.fecha_liberacion
        modelo.compromiso_contenido = getattr(garantia, "compromiso", "")
        return modelo

    def guardar(self, garantia: Garantia) -> None:
        """Persistir o actualizar una garantía en la base de datos.

        El commit es manejado por la capa de unidad de trabajo del servicio.
        """
        self._to_model(garantia)

    def obtener_por_id(self, id: UUID) -> Garantia | None:
        modelo = self._session.get(GarantiaModel, id)
        if modelo is None:
            return None
        return self._to_entity(modelo)
