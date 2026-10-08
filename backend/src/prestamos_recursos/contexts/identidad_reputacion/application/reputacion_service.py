from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import (
    ExcepcionAcademicaDTO,
    PerfilReputacionDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import (
    PerfilReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.excepcion_academica_repository import (
    ExcepcionAcademicaRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.perfil_reputacion_repository import (
    PerfilReputacionRepository,
)


class ReputacionService:
    """Servicio de aplicación para gestión de reputación y sanciones."""

    def __init__(
        self,
        perfil_reputacion_repository: PerfilReputacionRepository,
        excepcion_academica_repository: ExcepcionAcademicaRepository,
    ) -> None:
        self._perfil_reputacion_repository = perfil_reputacion_repository
        self._excepcion_academica_repository = excepcion_academica_repository

    def obtener_perfil(self, usuario_id: UUID) -> PerfilReputacionDTO:
        """
        Obtiene el perfil de reputación de un usuario.

        Si no existe, lo crea usando la factory (puntaje 500, nivel NORMAL).
        Retorna el perfil como DTO.
        """
        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)

        if perfil is None:
            # Crear perfil nuevo usando factory del dominio
            perfil = PerfilReputacion.crear_para_usuario(usuario_id)
            self._perfil_reputacion_repository.guardar(perfil)

        return PerfilReputacionDTO.from_entity(perfil)

    def es_elegible_para_prestamo(self, usuario_id: UUID) -> bool:
        """
        Determina si un usuario es elegible para realizar un préstamo.

        Obtiene el perfil y las excepciones académicas vigentes,
        delega la decisión a la entidad PerfilReputacion.
        """
        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)

        if perfil is None:
            # Si no tiene perfil, se crea uno (factory) y es elegible (NORMAL, sin sanciones)
            perfil = PerfilReputacion.crear_para_usuario(usuario_id)
            self._perfil_reputacion_repository.guardar(perfil)
            return True

        # Obtener excepciones vigentes del usuario
        excepciones_vigentes = self._excepcion_academica_repository.obtener_vigentes_por_usuario(
            usuario_id
        )

        # Delegar a la entidad de dominio
        return perfil.es_elegible_para_prestamo(excepciones_vigentes)

    def aplicar_sancion(
        self, usuario_id: UUID, tipo: TipoSancion, motivo: str
    ) -> None:
        """
        Aplica una sanción al usuario.

        - Obtiene/crea el perfil de reputación
        - Crea una Sancion con descuentos según TipoSancion
        - Llama a perfil.aplicar_sancion(sancion) que actualiza puntos y nivel
        - Persiste todo atómicamente via repository
        """
        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)

        if perfil is None:
            perfil = PerfilReputacion.crear_para_usuario(usuario_id)

        # Crear sanción con valores según TipoSancion
        sancion = Sancion(
            tipo=tipo,
            puntos_descuento=tipo.puntos_descuento,
            monto_descuento=Decimal(tipo.monto_descuento),
            motivo=motivo,
            fecha_aplicacion=datetime.now(UTC),
        )

        # Aplicar sanción al perfil (añade a lista, descuenta puntos, recalcula nivel)
        perfil.aplicar_sancion(sancion)

        # Persistir cambios (perfil + sanciones en una transacción)
        self._perfil_reputacion_repository.guardar(perfil)

    def registrar_excepcion(
        self,
        usuario_id: UUID,
        motivo: str,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> ExcepcionAcademicaDTO:
        """
        Registra una excepción académica para un usuario.

        Crea la excepción, la persiste y retorna su DTO.
        """
        excepcion = ExcepcionAcademica(
            usuario_id=usuario_id,
            motivo=motivo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activa=True,
        )

        self._excepcion_academica_repository.guardar(excepcion)

        return ExcepcionAcademicaDTO.from_entity(excepcion)