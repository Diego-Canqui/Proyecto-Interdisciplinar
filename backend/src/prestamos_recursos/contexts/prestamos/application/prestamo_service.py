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
            if hasattr(self._reputacion_service, "premiar_entrega_puntual"):
                self._reputacion_service.premiar_entrega_puntual(prestamo.usuario_id)

    def completar_entrega(
        self,
        id_prestamo: UUID,
        tipo_garantia: TipoGarantia,
        compromiso: CompromisoResponsabilidad,
        observaciones_checklist: str,
        fotos_urls: list[str] | None = None,
    ) -> None:
        """Realiza el ciclo completo de inspección y entrega en ventanilla."""
        self.iniciar_entrega(id_prestamo, tipo_garantia, compromiso)
        self.agregar_item_checklist(id_prestamo, observaciones_checklist, fotos_urls or [])
        self.confirmar_entrega(id_prestamo)
        self.finalizar_entrega(id_prestamo)

    def consultar_inspecciones(self, id_prestamo: UUID) -> dict:
        """Devuelve los registros de garantía y checklist de un préstamo."""
        inicial = (
            self._checklist_repository.obtener_por_prestamo_y_tipo(
                id_prestamo, TipoChecklist.ESTADO_INICIAL
            )
            if hasattr(self._checklist_repository, "obtener_por_prestamo_y_tipo")
            else None
        )
        retorno = (
            self._checklist_repository.obtener_por_prestamo_y_tipo(
                id_prestamo, TipoChecklist.ESTADO_DEVOLUCION
            )
            if hasattr(self._checklist_repository, "obtener_por_prestamo_y_tipo")
            else None
        )
        garantia = (
            self._garantia_repository.obtener_por_prestamo(id_prestamo)
            if hasattr(self._garantia_repository, "obtener_por_prestamo")
            else None
        )

        return {
            "prestamo_id": id_prestamo,
            "checklist_inicial": (
                {
                    "fecha_inspeccion": inicial.fecha_inspeccion,
                    "observaciones": inicial.observaciones,
                    "fotos_urls": inicial.fotos_urls,
                    "completo": inicial.completo,
                }
                if inicial
                else None
            ),
            "checklist_devolucion": (
                {
                    "fecha_inspeccion": retorno.fecha_inspeccion,
                    "observaciones": retorno.observaciones,
                    "fotos_urls": retorno.fotos_urls,
                    "completo": retorno.completo,
                }
                if retorno
                else None
            ),
            "garantia": (
                {
                    "tipo": garantia.tipo.value,
                    "estado": garantia.estado.value,
                    "fecha_registro": garantia.fecha_registro,
                    "testigo": garantia.compromiso.testigo,
                }
                if garantia
                else None
            ),
        }

    def _obtener_prestamo_activo(self, id_prestamo: UUID) -> Prestamo:
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")
        if prestamo.estado != EstadoPrestamo.ACTIVO:
            raise ValueError("El préstamo no está activo")
        return prestamo

    def procesar_devolucion(
        self,
        id_prestamo: UUID,
        observaciones_retorno: str = "Devuelto conforme",
        fotos_urls: list[str] | None = None,
        danos_detectados: bool = False,
    ) -> int:
        """Procesa la devolución de un préstamo con checklist de recepción y actualiza reputación."""
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")

        dias_retraso = prestamo.devolver()
        self._prestamo_repository.guardar(prestamo)

        # Registrar inspección de recepción/devolución si el repositorio lo soporta
        if hasattr(self._checklist_repository, "guardar"):
            checklist_retorno = Checklist(
                prestamo_id=id_prestamo,
                tipo=TipoChecklist.ESTADO_DEVOLUCION,
                fecha_inspeccion=datetime.now(UTC),
                observaciones=observaciones_retorno,
                fotos_urls=fotos_urls or [],
                completo=True,
            )
            self._checklist_repository.guardar(checklist_retorno)

        # Liberar recurso (si hay daños, ponerlo en mantenimiento para revisión)
        if self._recurso_repository is not None:
            nuevo_estado = (
                EstadoRecurso.MANTENIMIENTO if danos_detectados else EstadoRecurso.DISPONIBLE
            )
            self._recurso_repository.actualizar_estado(prestamo.recurso_id, nuevo_estado)

        if self._reputacion_service is None:
            return dias_retraso

        # Aplicar sanción por daño físico si fue detectado en la inspección
        if danos_detectados and hasattr(self._reputacion_service, "aplicar_sancion"):
            self._reputacion_service.aplicar_sancion(
                prestamo.usuario_id,
                TipoSancion.DANO_PARCIAL,
                motivo=f"Daños físicos en recepción: {observaciones_retorno}",
            )

        # Penalización o premio por puntualidad
        if dias_retraso == 0:
            if not danos_detectados and hasattr(self._reputacion_service, "premiar_devolucion_puntual"):
                self._reputacion_service.premiar_devolucion_puntual(prestamo.usuario_id)
        else:
            if hasattr(self._reputacion_service, "aplicar_sancion"):
                self._reputacion_service.aplicar_sancion(
                    prestamo.usuario_id,
                    TipoSancion.TARDANZA,
                    motivo="Devolución tardía",
                    dias_retardo=dias_retraso,
                )
        return dias_retraso

    def renovar_prestamo(self, id_prestamo: UUID) -> bool:
        """Renueva un préstamo activo extendiendo su fecha de fin por 7 días."""
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")
        prestamo.renovar(dias=7)
        self._prestamo_repository.guardar(prestamo)
        return True

    def validar_reglas_negocio(self) -> bool:
        """Placeholder para validar reglas de negocio del préstamo."""
        return True

    def consultar_historial(self, id_usuario: UUID) -> list[PrestamoDTO]:
        prestamos = self._prestamo_repository.obtener_por_usuario(id_usuario)
        return [PrestamoDTO.from_entity(p) for p in prestamos]

    def consultar_todos(self) -> list[PrestamoDTO]:
        prestamos = self._prestamo_repository.obtener_todos()
        return [PrestamoDTO.from_entity(p) for p in prestamos]
