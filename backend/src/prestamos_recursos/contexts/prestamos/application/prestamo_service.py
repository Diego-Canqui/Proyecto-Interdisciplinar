from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.catalogo.domain.repositories.recurso_repository import (
    RecursoRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.application.reputacion_service import (
    ReputacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.prestamos.application.dto.prestamo_dto import PrestamoDTO
from prestamos_recursos.contexts.prestamos.domain.entities.checklist import Checklist
from prestamos_recursos.contexts.prestamos.domain.entities.garantia import Garantia
from prestamos_recursos.contexts.prestamos.domain.entities.prestamo import Prestamo
from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.estado_prestamo import EstadoPrestamo
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.domain.repositories.checklist_repository import (
    ChecklistRepository,
)
from prestamos_recursos.contexts.prestamos.domain.repositories.garantia_repository import (
    GarantiaRepository,
)
from prestamos_recursos.contexts.prestamos.domain.repositories.prestamo_repository import (
    PrestamoRepository,
)
from prestamos_recursos.contexts.prestamos.domain.value_objects.compromiso_responsabilidad import (
    CompromisoResponsabilidad,
)


class PrestamoService:
    """«Service» PrestamoService."""

    def __init__(
        self,
        prestamo_repository: PrestamoRepository,
        checklist_repository: ChecklistRepository,
        garantia_repository: GarantiaRepository,
        reputacion_service: ReputacionService | None = None,
        recurso_repository: RecursoRepository | None = None,
    ) -> None:
        self._prestamo_repository = prestamo_repository
        self._checklist_repository = checklist_repository
        self._garantia_repository = garantia_repository
        self._reputacion_service = reputacion_service
        self._recurso_repository = recurso_repository

    def solicitar_prestamo(
        self,
        id_reserva: UUID,
        id_usuario: UUID,
        id_recurso: UUID,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> bool:
        """Crea un préstamo desde una reserva tras validar el recurso del catálogo."""
        if self._recurso_repository is None:
            raise RuntimeError("El repositorio de catálogo no está configurado")

        recurso = self._recurso_repository.obtener_por_id(id_recurso)
        if recurso is None:
            raise ValueError("Recurso no encontrado")
        if recurso.estado != EstadoRecurso.DISPONIBLE:
            raise ValueError("Recurso no disponible")

        prestamo = Prestamo(
            reserva_id=id_reserva,
            usuario_id=id_usuario,
            recurso_id=id_recurso,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=EstadoPrestamo.ACTIVO,
        )
        self._prestamo_repository.guardar(prestamo)
        self._recurso_repository.actualizar_estado(id_recurso, EstadoRecurso.EN_USO)
        return True

    def crear_desde_reserva(
        self,
        id_reserva: UUID,
        id_usuario: UUID,
        id_recurso: UUID,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> bool:
        """Compatibilidad: crea un préstamo desde una reserva confirmada."""
        return self.solicitar_prestamo(
            id_reserva=id_reserva,
            id_usuario=id_usuario,
            id_recurso=id_recurso,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    def iniciar_entrega(
        self,
        id_prestamo: UUID,
        tipo_garantia: TipoGarantia,
        compromiso: CompromisoResponsabilidad,
    ) -> None:
        """Inicia el ciclo de entrega creando garantía y checklist.

        - El préstamo debe existir y estar en estado ``ACTIVO``.
        - Se crea una ``Garantia`` con estado ``PENDIENTE``.
        - Se crea un ``Checklist`` de tipo ``ESTADO_INICIAL``.
        - Ambos objetos se persisten mediante sus repositorios.
        """
        # Obtener préstamo
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")
        if prestamo.estado != EstadoPrestamo.ACTIVO:
            raise ValueError("Sólo pueden entregarse préstamos activos")

        # ---------- Garantía ----------
        garantia = Garantia(
            prestamo_id=id_prestamo,
            tipo=tipo_garantia,
            estado=EstadoGarantia.PENDIENTE,
            fecha_registro=datetime.now(UTC),
            compromiso=compromiso,
        )
        self._garantia_repository.guardar(garantia)

        # ---------- Checklist ----------
        checklist = Checklist(
            prestamo_id=id_prestamo,
            tipo=TipoChecklist.ESTADO_INICIAL,
            fecha_inspeccion=datetime.now(UTC),
            observaciones="",
            completo=False,
        )
        self._checklist_repository.guardar(checklist)

    def agregar_item_checklist(
        self, id_prestamo: UUID, observaciones: str, fotos_urls: list[str]
    ) -> None:
        prestamo = self._obtener_prestamo_activo(id_prestamo)
        checklist = self._checklist_repository.obtener_por_prestamo_y_tipo(
            prestamo.id, TipoChecklist.ESTADO_INICIAL
        )
        if checklist is None:
            raise ValueError("No se ha iniciado la entrega")
        checklist.agregar_item(observaciones, fotos_urls)
        self._checklist_repository.guardar(checklist)

    def confirmar_entrega(self, id_prestamo: UUID) -> None:
        prestamo = self._obtener_prestamo_activo(id_prestamo)
        checklist = self._checklist_repository.obtener_por_prestamo_y_tipo(
            prestamo.id, TipoChecklist.ESTADO_INICIAL
        )
        if checklist is None:
            raise ValueError("No se ha iniciado la entrega")
        garantia = self._garantia_repository.obtener_por_prestamo(prestamo.id)
        if garantia is None:
            raise ValueError("No se ha registrado la garantía")
        checklist.confirmar()
        garantia.registrar()
        self._checklist_repository.guardar(checklist)
        self._garantia_repository.guardar(garantia)

    def finalizar_entrega(self, id_prestamo: UUID) -> None:
        prestamo = self._obtener_prestamo_activo(id_prestamo)
        checklist = self._checklist_repository.obtener_por_prestamo_y_tipo(
            prestamo.id, TipoChecklist.ESTADO_INICIAL
        )
        if checklist is None or not checklist.completo:
            raise ValueError("Debe confirmarse el checklist antes de finalizar la entrega")
        garantia = self._garantia_repository.obtener_por_prestamo(prestamo.id)
        if garantia is None or garantia.estado != EstadoGarantia.REGISTRADA:
            raise ValueError("Debe confirmarse la garantía antes de finalizar la entrega")

        fecha_inicio = prestamo.fecha_inicio
        if fecha_inicio.tzinfo is None:
            fecha_inicio = fecha_inicio.replace(tzinfo=UTC)
        puntual = datetime.now(UTC).date() <= fecha_inicio.astimezone(UTC).date()
        prestamo.marcar_entregado()
        self._prestamo_repository.guardar(prestamo)
        if puntual and self._reputacion_service is not None:
            self._reputacion_service.premiar_entrega_puntual(prestamo.usuario_id)

    def _obtener_prestamo_activo(self, id_prestamo: UUID) -> Prestamo:
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")
        if prestamo.estado != EstadoPrestamo.ACTIVO:
            raise ValueError("El préstamo no está activo")
        return prestamo

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

        if self._reputacion_service is None:
            return

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
        """Renueva un préstamo activo extendiendo su fecha de fin.

        Por ahora, extiende 7 días. Se puede parametrizar según requerimientos.
        """
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")
        # Extender 7 días como ejemplo
        prestamo.renovar(dias=7)
        self._prestamo_repository.guardar(prestamo)
        return True

    def validar_reglas_negocio(self) -> bool:
        """Placeholder para validar reglas de negocio del préstamo."""
        return True

    def consultar_historial(self, id_usuario: UUID) -> list[PrestamoDTO]:
        prestamos = self._prestamo_repository.obtener_por_usuario(id_usuario)
        return [PrestamoDTO.from_entity(p) for p in prestamos]
