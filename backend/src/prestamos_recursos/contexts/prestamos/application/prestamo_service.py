from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso

if TYPE_CHECKING:
    from prestamos_recursos.contexts.catalogo.application.services import (
        RecursoApplicationService,
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
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_dano_devolucion import (
    TipoDanoDevolucion,
)
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
from prestamos_recursos.contexts.prestamos.domain.services.plantilla_checklist import (
    obtener_items_checklist_por_categoria,
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
        catalogo_service: RecursoApplicationService | None = None,
        recurso_repository: Any | None = None,
    ) -> None:
        self._prestamo_repository = prestamo_repository
        self._checklist_repository = checklist_repository
        self._garantia_repository = garantia_repository
        self._reputacion_service = reputacion_service
        self._recurso_repository = catalogo_service or recurso_repository

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
        if (
            puntual
            and self._reputacion_service is not None
            and hasattr(self._reputacion_service, "premiar_entrega_puntual")
        ):
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
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")

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
                    "fecha_liberacion": garantia.fecha_liberacion,
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

    def obtener_plantilla_checklist(self, id_prestamo: UUID) -> dict[str, Any]:
        """Determina la plantilla de checklist de entrega según la categoría del recurso."""
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")

        categoria = ""
        if self._recurso_repository is not None and hasattr(
            self._recurso_repository, "obtener_por_id"
        ):
            recurso = self._recurso_repository.obtener_por_id(prestamo.recurso_id)
            if recurso is not None and getattr(recurso, "categoria", None):
                categoria = str(recurso.categoria)

        return {
            "prestamo_id": prestamo.id,
            "recurso_id": prestamo.recurso_id,
            "categoria": categoria,
            "items": obtener_items_checklist_por_categoria(categoria),
        }

    def procesar_devolucion(
        self,
        id_prestamo: UUID,
        observaciones_retorno: str = "Devuelto conforme",
        fotos_urls: list[str] | None = None,
        danos_detectados: bool = False,
        tipo_dano: TipoDanoDevolucion = TipoDanoDevolucion.NINGUNO,
        monto_dano: Decimal | None = None,
        fecha_devolucion: datetime | None = None,
    ) -> int:
        """Procesa la devolución de un préstamo y retorna los días de retraso."""
        resultado = self.procesar_devolucion_detallada(
            id_prestamo=id_prestamo,
            observaciones_retorno=observaciones_retorno,
            fotos_urls=fotos_urls,
            danos_detectados=danos_detectados,
            tipo_dano=tipo_dano,
            monto_dano=monto_dano,
            fecha_devolucion=fecha_devolucion,
        )
        return int(resultado["dias_retraso"])

    def procesar_devolucion_detallada(
        self,
        id_prestamo: UUID,
        observaciones_retorno: str = "Devuelto conforme",
        fotos_urls: list[str] | None = None,
        danos_detectados: bool = False,
        tipo_dano: TipoDanoDevolucion = TipoDanoDevolucion.NINGUNO,
        monto_dano: Decimal | None = None,
        fecha_devolucion: datetime | None = None,
    ) -> dict[str, Any]:
        """Procesa la devolución con tipo de daño, puntualidad exacta y reputación."""
        tipo_efectivo = (
            TipoDanoDevolucion.DANO_PARCIAL
            if tipo_dano == TipoDanoDevolucion.NINGUNO and danos_detectados
            else tipo_dano
        )
        if tipo_efectivo == TipoDanoDevolucion.DANO_TOTAL and (
            monto_dano is None or monto_dano <= 0
        ):
            raise ValueError("Para daño total se debe indicar un monto mayor a cero")

        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")

        dias_retraso = prestamo.devolver(fecha_devolucion)
        puntual = prestamo.es_devolucion_puntual()
        hubo_danos = tipo_efectivo != TipoDanoDevolucion.NINGUNO
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

        # Liberar o retener garantía asociada si existe (RF-05)
        if self._garantia_repository is not None and hasattr(
            self._garantia_repository, "obtener_por_prestamo"
        ):
            garantia = self._garantia_repository.obtener_por_prestamo(id_prestamo)
            if garantia is not None and garantia.estado in {
                EstadoGarantia.REGISTRADA,
                EstadoGarantia.PENDIENTE,
            }:
                if hubo_danos:
                    garantia.retener()
                else:
                    garantia.liberar(datetime.now(UTC))
                if hasattr(self._garantia_repository, "guardar"):
                    self._garantia_repository.guardar(garantia)

        # Actualizar estado del recurso según el tipo de daño observado
        if self._recurso_repository is not None:
            estado_por_dano = {
                TipoDanoDevolucion.NINGUNO: EstadoRecurso.DISPONIBLE,
                TipoDanoDevolucion.DANO_PARCIAL: EstadoRecurso.MANTENIMIENTO,
                TipoDanoDevolucion.DANO_TOTAL: EstadoRecurso.FUERA_DE_SERVICIO,
            }
            self._recurso_repository.actualizar_estado(
                prestamo.recurso_id, estado_por_dano[tipo_efectivo]
            )

        self._aplicar_reputacion_devolucion(
            usuario_id=prestamo.usuario_id,
            tipo_efectivo=tipo_efectivo,
            monto_dano=monto_dano,
            observaciones_retorno=observaciones_retorno,
            dias_retraso=dias_retraso,
            puntual=puntual,
        )

        return {
            "dias_retraso": dias_retraso,
            "puntual": puntual,
            "tipo_dano": tipo_efectivo.value,
        }

    def _aplicar_reputacion_devolucion(
        self,
        usuario_id: UUID,
        tipo_efectivo: TipoDanoDevolucion,
        monto_dano: Decimal | None,
        observaciones_retorno: str,
        dias_retraso: int,
        puntual: bool,
    ) -> None:
        if self._reputacion_service is None:
            return

        if hasattr(self._reputacion_service, "aplicar_sancion"):
            if tipo_efectivo == TipoDanoDevolucion.DANO_PARCIAL:
                self._reputacion_service.aplicar_sancion(
                    usuario_id,
                    TipoSancion.DANO_PARCIAL,
                    motivo=f"Daños físicos en recepción: {observaciones_retorno}",
                )
            elif tipo_efectivo == TipoDanoDevolucion.DANO_TOTAL:
                self._reputacion_service.aplicar_sancion(
                    usuario_id,
                    TipoSancion.DANO_TOTAL,
                    motivo=f"Daño total en recepción: {observaciones_retorno}",
                    monto_opcional=monto_dano,
                )

            if dias_retraso > 0:
                self._reputacion_service.aplicar_sancion(
                    usuario_id,
                    TipoSancion.TARDANZA,
                    motivo="Devolución tardía",
                    dias_retardo=dias_retraso,
                )

        if (
            puntual
            and tipo_efectivo == TipoDanoDevolucion.NINGUNO
            and hasattr(self._reputacion_service, "premiar_devolucion_puntual")
        ):
            self._reputacion_service.premiar_devolucion_puntual(usuario_id)

    def renovar_prestamo(self, id_prestamo: UUID) -> bool:
        """Las renovaciones de préstamos están deshabilitadas por política operativa."""
        raise ValueError("Renovación de préstamos no permitida")

    def validar_reglas_negocio(self) -> bool:
        """Placeholder para validar reglas de negocio del préstamo."""
        return True

    def obtener_prestamo(self, id_prestamo: UUID) -> PrestamoDTO | None:
        """Obtiene un préstamo por su identificador como DTO."""
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            return None
        return PrestamoDTO.from_entity(prestamo)

    def consultar_historial(self, id_usuario: UUID) -> list[PrestamoDTO]:
        prestamos = self._prestamo_repository.obtener_por_usuario(id_usuario)
        return [PrestamoDTO.from_entity(p) for p in prestamos]

    def consultar_todos(self) -> list[PrestamoDTO]:
        prestamos = self._prestamo_repository.obtener_todos()
        return [PrestamoDTO.from_entity(p) for p in prestamos]

    def cancelar_prestamo(self, id_prestamo: UUID, motivo: str = "") -> PrestamoDTO:
        """Cancela administrativamente un préstamo pendiente de entrega física y libera el recurso."""
        prestamo = self._prestamo_repository.obtener_por_id(id_prestamo)
        if prestamo is None:
            raise ValueError("Préstamo no encontrado")

        prestamo.cancelar(motivo)
        self._prestamo_repository.guardar(prestamo)

        if self._recurso_repository is not None:
            self._recurso_repository.actualizar_estado(
                prestamo.recurso_id, EstadoRecurso.DISPONIBLE
            )

        return PrestamoDTO.from_entity(prestamo)

    def contar_prestamos_en_curso(self, id_usuario: UUID) -> int:
        """Cuenta los préstamos en curso del usuario (ACTIVO, ENTREGADO o VENCIDO)."""
        prestamos = self._prestamo_repository.obtener_por_usuario(id_usuario)
        estados_en_curso = {
            EstadoPrestamo.ACTIVO,
            EstadoPrestamo.ENTREGADO,
            EstadoPrestamo.VENCIDO,
        }
        return sum(1 for p in prestamos if p.estado in estados_en_curso)

