from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import (
    ElegibilidadDTO,
    ExcepcionAcademicaDTO,
    PerfilReputacionDTO,
    SancionDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.excepciones import (
    ExcepcionNoEncontrada,
    SancionInvalida,
    UsuarioNoEncontrado,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import (
    PerfilReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.excepcion_academica_repository import (
    ExcepcionAcademicaRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.perfil_reputacion_repository import (
    PerfilReputacionRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import (
    UsuarioRepository,
)


class ReputacionService:
    """Servicio de aplicación para gestión de reputación y sanciones."""

    def __init__(
        self,
        perfil_reputacion_repository: PerfilReputacionRepository,
        excepcion_academica_repository: ExcepcionAcademicaRepository,
        usuario_repository: UsuarioRepository,
    ) -> None:
        self._perfil_reputacion_repository = perfil_reputacion_repository
        self._excepcion_academica_repository = excepcion_academica_repository
        self._usuario_repository = usuario_repository

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

    def obtener_elegibilidad(self, usuario_id: UUID) -> ElegibilidadDTO:
        """
        Consulta la elegibilidad del usuario con la razón del bloqueo (RF-21).

        - El nivel de reputación no participa (RF-01)
        - Perfil y excepciones se obtienen con el mismo criterio que
          es_elegible_para_prestamo (sin perfil → se crea y es elegible)
        - Si no es elegible, la razón incluye el tipo de la sanción bloqueante y su
          fecha de fin en lenguaje de negocio (D9: el dominio dice QUÉ bloquea,
          el servicio redacta la razón)
        """
        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)

        if perfil is None:
            # Si no tiene perfil, se crea uno (factory) y es elegible (NORMAL, sin sanciones)
            perfil = PerfilReputacion.crear_para_usuario(usuario_id)
            self._perfil_reputacion_repository.guardar(perfil)

        excepciones_vigentes = self._excepcion_academica_repository.obtener_vigentes_por_usuario(
            usuario_id
        )

        sancion_bloqueante = perfil.sancion_bloqueante(excepciones_vigentes)

        if sancion_bloqueante is None:
            return ElegibilidadDTO(elegible=True)

        razon = (
            f"tienes una sanción vigente de tipo {sancion_bloqueante.tipo.value} "
            f"hasta {sancion_bloqueante.fecha_fin:%Y-%m-%d}"
        )
        return ElegibilidadDTO(elegible=False, razon=razon)

    def aplicar_sancion(
        self,
        usuario_id: UUID,
        tipo: TipoSancion,
        motivo: str,
        monto_opcional: Decimal | None = None,
        dias_retardo: int | None = None,
    ) -> SancionDTO:
        """
        Aplica una sanción al usuario y devuelve el DTO de la sanción creada (RF-08).

        - RF-23: verifica que el usuario exista antes de operar (sin perfiles huérfanos)
        - RF-06/RF-07: valida y normaliza las premisas por tipo (SancionInvalida, sin HTTP)
        - RF-03/RF-05: `fecha_fin` se deriva de `TipoSancion.duracion_bloqueo`
        - Obtiene/crea el perfil de reputación
        - Llama a perfil.aplicar_sancion(sancion) que actualiza puntos y nivel
        - Persiste todo atómicamente via repository
        """
        self._verificar_usuario_existe(usuario_id)

        # Premisas ya validadas: dan la deuda a registrar y los días de retraso efectivos
        monto_descuento, dias_retraso = self._premisas_sancion(
            tipo, monto_opcional, dias_retardo
        )

        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)

        if perfil is None:
            perfil = PerfilReputacion.crear_para_usuario(usuario_id)

        # Crear sanción con valores según TipoSancion
        fecha_aplicacion = datetime.now(UTC)
        sancion = Sancion(
            tipo=tipo,
            puntos_descuento=tipo.puntos_descuento,
            monto_descuento=monto_descuento,
            motivo=motivo,
            fecha_aplicacion=fecha_aplicacion,
            fecha_fin=fecha_aplicacion + timedelta(days=tipo.duracion_bloqueo(dias_retraso)),
        )

        # Aplicar sanción al perfil (añade a lista, descuenta puntos, recalcula nivel)
        perfil.aplicar_sancion(sancion)

        # Persistir cambios (perfil + sanciones en una transacción)
        self._perfil_reputacion_repository.guardar(perfil)

        return SancionDTO.from_entity(sancion)

    def premiar_devolucion_puntual(self, usuario_id: UUID) -> None:
        """
        Premia la devolución puntual de un usuario (RF-10).

        - RF-23: verifica que el usuario exista antes de operar (sin perfiles huérfanos)
        - Autocrea el perfil (500, NORMAL) si no existe → el premio lo deja en 510
        - Suma 10 puntos con tope 1000, recalcula el nivel y persiste
        """
        self._verificar_usuario_existe(usuario_id)

        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)

        if perfil is None:
            perfil = PerfilReputacion.crear_para_usuario(usuario_id)

        perfil.premiar_puntualidad()

        self._perfil_reputacion_repository.guardar(perfil)

    def premiar_entrega_puntual(self, usuario_id: UUID) -> None:
        """Aplica la bonificación de puntualidad definida para entregas a tiempo."""
        self.premiar_devolucion_puntual(usuario_id)

    def ejecutar_amnistia_mensual(self) -> int:
        """
        Ejecuta la amnistía mensual y devuelve cuántos perfiles premió (RF-11, RF-13).

        - Recorre solo los perfiles en nivel BAJO (RF-12: otros niveles no reciben amnistía)
        - La regla de los 30 días vive en el dominio (`aplicar_amnistia`); 0 premiados
          es un resultado válido
        - Persiste cada perfil premiado (con su nivel recalculado)
        """
        perfiles_bajos = self._perfil_reputacion_repository.obtener_por_nivel(
            NivelReputacion.BAJO
        )

        perfiles_premiados = 0
        for perfil in perfiles_bajos:
            if perfil.aplicar_amnistia():
                self._perfil_reputacion_repository.guardar(perfil)
                perfiles_premiados += 1

        return perfiles_premiados

    def _verificar_usuario_existe(self, usuario_id: UUID) -> None:
        """RF-23: verifica que el usuario esté registrado antes de operar sobre su reputación."""
        if self._usuario_repository.obtener_por_id(usuario_id) is None:
            raise UsuarioNoEncontrado("Usuario no encontrado")

    @staticmethod
    def _premisas_sancion(
        tipo: TipoSancion, monto_opcional: Decimal | None, dias_retardo: int | None
    ) -> tuple[Decimal, int]:
        """
        Valida y normaliza las premisas de la sanción (RF-06/RF-07) — D5.

        Se re-valida aquí, y no solo en `AplicarSancionDTO`, porque el contexto
        `prestamos` llama al servicio sin pasar por HTTP. Devuelve la deuda a
        registrar y los días de retraso efectivos: los parámetros que no aplican
        al tipo se ignoran y se registra la deuda fija del tipo.
        """
        if tipo == TipoSancion.TARDANZA:
            # Un usuario puntual nunca se sanciona por tardanza: exige dias_retardo >= 1
            if dias_retardo is None or dias_retardo < 1:
                raise SancionInvalida("TARDANZA exige dias_retardo >= 1")
            return Decimal(tipo.monto_descuento), dias_retardo

        if tipo == TipoSancion.DANO_TOTAL:
            # La deuda de un recurso destruido no puede registrarse como $0
            if monto_opcional is None or monto_opcional <= 0:
                raise SancionInvalida("DANO_TOTAL exige monto_opcional > 0")
            return monto_opcional, 0

        # Tipos de duración y deuda fijas: ignoran monto_opcional y dias_retardo
        return Decimal(tipo.monto_descuento), 0

    def registrar_excepcion(
        self,
        usuario_id: UUID,
        motivo: str,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> ExcepcionAcademicaDTO:
        """
        Registra una excepción académica para un usuario.

        - RF-23: verifica que el usuario exista antes de operar (sin excepciones huérfanas)
        - Crea la excepción, la persiste y retorna su DTO.
        """
        self._verificar_usuario_existe(usuario_id)

        excepcion = ExcepcionAcademica(
            usuario_id=usuario_id,
            motivo=motivo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activa=True,
        )

        self._excepcion_academica_repository.guardar(excepcion)

        return ExcepcionAcademicaDTO.from_entity(excepcion)

    def anular_excepcion(self, excepcion_id: UUID) -> ExcepcionAcademicaDTO:
        """
        Anula una excepción académica por su identificador (RF-22).

        - Idempotente: anular una excepción ya anulada (o vencida) devuelve su DTO
        - `ExcepcionNoEncontrada` si el identificador no existe (RF-23, sin HTTP)
        """
        excepcion = self._excepcion_academica_repository.obtener_por_id(excepcion_id)

        if excepcion is None:
            raise ExcepcionNoEncontrada("Excepción no encontrada")

        # D10: la anulación es una operación de negocio del dominio
        excepcion.anular()
        self._excepcion_academica_repository.guardar(excepcion)

        return ExcepcionAcademicaDTO.from_entity(excepcion)