from __future__ import annotations

from datetime import datetime
from uuid import UUID

from prestamos_recursos.contexts.prestamos.application.dto.prestamo_dto import PrestamoDTO
from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.domain.repositories.checklist_repository import ChecklistRepository
from prestamos_recursos.contexts.prestamos.domain.repositories.garantia_repository import GarantiaRepository
from prestamos_recursos.contexts.identidad_reputacion.application.reputacion_service import ReputacionService
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion


class PrestamoService:
    """«Service» PrestamoService."""

    def __init__(self, prestamo_repository: PrestamoRepository, checklist_repository: ChecklistRepository, garantia_repository: GarantiaRepository, reputacion_service: ReputacionService = None) -> None:
        self._prestamo_repository = prestamo_repository
        self._checklist_repository = checklist_repository
        self._garantia_repository = garantia_repository
        self._reputacion_service = reputacion_service

    def solicitar_prestamo(self, id_usuario: UUID, id_recurso: UUID) -> bool:
        raise NotImplementedError

    def crear_desde_reserva(
        self,
        id_reserva: UUID,
        id_usuario: UUID,
        id_recurso: UUID,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> bool:
        prestamo = Prestamo(
            reserva_id=id_reserva,
            recurso_id=id_recurso,
            usuario_id=id_usuario,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=EstadoPrestamo.ACTIVO,
        )
        self._prestamo_repository.guardar(prestamo)
        return True

    def procesar_devolucion(self, id_prestamo: UUID) -> None:
        """Procesa la devolución de un préstamo y actualiza la reputación.

        - Obtiene el préstamo.
        - Llama a `prestamo.devolver()` que devuelve los días de retraso.
        - Si no hay retraso, premia al usuario.
        - Si hay retraso, aplica sanción de tardanza.
        """
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")
        dias_retraso = prestamo.devolver()
        # Persistir cambios del préstamo
        self._prestamo_repository.guardar(prestamo)
        if dias_retraso == 0:
            self._reputacion_service.premiar_devolucion_puntual(prestamo.usuario_id)
        else:
            self._reputacion_service.aplicar_sancion(
                prestamo.usuario_id,
                TipoSancion.TARDANZA,
                motivo="Devolución tardía",
                dias_retardo=dias_retraso,
            )

    def renovar_prestamo(self, id_prestamo: UUID) -> bool:
        raise NotImplementedError

    def validar_reglas_negocio(self) -> bool:
        raise NotImplementedError

    def consultar_historial(self, id_usuario: UUID) -> list[PrestamoDTO]:
        prestamos = self._prestamo_repository.obtener_por_usuario(id_usuario)
        return [PrestamoDTO.from_entity(p) for p in prestamos]

    """«Service» PrestamoService."""

    def __init__(self, prestamo_repository: PrestamoRepository, checklist_repository: ChecklistRepository, garantia_repository: GarantiaRepository) -> None:
        self._prestamo_repository = prestamo_repository
        self._checklist_repository = checklist_repository
        self._garantia_repository = garantia_repository

    def solicitar_prestamo(self, id_usuario: UUID, id_recurso: UUID) -> bool:
        raise NotImplementedError

    def crear_desde_reserva(
        self,
        id_reserva: UUID,
        id_usuario: UUID,
        id_recurso: UUID,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> bool:
        prestamo = Prestamo(
            reserva_id=id_reserva,
            recurso_id=id_recurso,
            usuario_id=id_usuario,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=EstadoPrestamo.ACTIVO,
        )
        self._prestamo_repository.guardar(prestamo)
        return True

    def procesar_devolucion(self, id_prestamo: UUID) -> None:
        raise NotImplementedError

    def renovar_prestamo(self, id_prestamo: UUID) -> bool:
        raise NotImplementedError

    def validar_reglas_negocio(self) -> bool:
        raise NotImplementedError

    def consultar_historial(self, id_usuario: UUID) -> list[PrestamoDTO]:
        prestamos = self._prestamo_repository.obtener_por_usuario(id_usuario)
        return [PrestamoDTO.from_entity(p) for p in prestamos]
