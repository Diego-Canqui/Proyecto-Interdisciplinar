from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import (
    ElegibilidadDTO,
    ExcepcionAcademicaDTO,
    MovimientoReputacionDTO,
    PerfilGestionDTO,
    PerfilReputacionDTO,
    SancionDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.excepciones import (
    ExcepcionNoEncontrada,
    SancionInvalida,
    UsuarioNoEncontrado,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities import (
    MovimientoReputacion,
    Usuario,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import (
    ExcepcionAcademica,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import (
    PerfilReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums import TipoMovimientoReputacion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import (
    NivelReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories import (
    MovimientoReputacionRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.excepcion_academica_repository import (
    ExcepcionAcademicaRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.perfil_reputacion_repository import (
    PerfilReputacionRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import (
    UsuarioRepository,
)

_PREFIJOS_FORMULA_CSV = ("=", "+", "-", "@", "\t", "\r")
_COLUMNAS_CSV = (
    "Usuario",
    "Correo",
    "Fecha",
    "Evento",
    "Motivo",
    "Recurso",
    "Puntaje anterior",
    "Variación",
    "Puntaje resultante",
)


class ReputacionService:
    """Servicio de aplicación para gestión de reputación y sanciones."""

    def __init__(
        self,
        perfil_reputacion_repository: PerfilReputacionRepository,
        excepcion_academica_repository: ExcepcionAcademicaRepository,
        usuario_repository: UsuarioRepository,
        movimiento_reputacion_repository: MovimientoReputacionRepository | None = None,
    ) -> None:
        self._perfil_reputacion_repository = perfil_reputacion_repository
        self._excepcion_academica_repository = excepcion_academica_repository
        self._usuario_repository = usuario_repository
        self._movimiento_reputacion_repository = movimiento_reputacion_repository

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

    def consultar_elegibilidad_lectura(self, usuario_id: UUID) -> ElegibilidadDTO:
        """
        Consulta la elegibilidad del usuario en modo solo lectura (RF-03).

        No crea ni persiste el perfil si no existe en la base de datos para no
        generar perfiles huérfanos ni errores de FK.
        """
        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)
        if perfil is None:
            return ElegibilidadDTO(elegible=True)

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

    def consultar_nivel_lectura(self, usuario_id: UUID) -> NivelReputacion:
        """
        Consulta el nivel de reputación en modo solo lectura (RF-04).

        Si no tiene perfil, retorna NORMAL por defecto sin insertar en la base de datos.
        """
        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)
        if perfil is None:
            return NivelReputacion.NORMAL
        return perfil.nivel

    def consultar_puntaje_lectura(self, usuario_id: UUID) -> int:
        """
        Consulta el puntaje de reputación en modo solo lectura (RF-04).

        Si no tiene perfil, retorna 500 por defecto sin insertar en la base de datos.
        """
        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)
        if perfil is None:
            return 500
        return perfil.puntaje.puntos


    def obtener_perfil_gestion(self, usuario_id: UUID) -> PerfilGestionDTO:
        """
        Consulta de solo lectura para los roles de gestión (RF-04).

        - 404 si el usuario no existe (sin autocrear perfiles, RF-23)
        - Sin perfil → 500/NORMAL, fecha_actualizacion=None y sanciones vacías (D5)
        - Devuelve TODAS las excepciones con su estado derivado (D4)
        - No escribe: no llama a guardar/flush (RNF-2)
        """
        self._verificar_usuario_existe(usuario_id)

        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)
        excepciones = self._excepcion_academica_repository.obtener_por_usuario(usuario_id)
        ahora = datetime.now(UTC)

        if perfil is None:
            return PerfilGestionDTO.sin_perfil(usuario_id, excepciones, ahora)
        return PerfilGestionDTO.from_entity(perfil, excepciones, ahora)

    def aplicar_sancion(
        self,
        usuario_id: UUID,
        tipo: TipoSancion,
        motivo: str,
        monto_opcional: Decimal | None = None,
        dias_retardo: int | None = None,
        *,
        prestamo_id: UUID | None = None,
        reserva_id: UUID | None = None,
        recurso_id: UUID | None = None,
        recurso_nombre: str | None = None,
    ) -> SancionDTO:
        """
        Aplica una sanción al usuario y devuelve el DTO de la sanción creada (RF-08).

        - RF-23: verifica que el usuario exista antes de operar (sin perfiles huérfanos)
        - RF-06/RF-07: valida y normaliza las premisas por tipo (SancionInvalida, sin HTTP)
        - RF-03/RF-05: `fecha_fin` se deriva de `TipoSancion.duracion_bloqueo`
        - Obtiene/crea el perfil de reputación
        - Llama a perfil.aplicar_sancion(sancion) que actualiza puntos y nivel
        - Persiste todo atómicamente via repository y registra movimiento en bitácora
        """
        self._verificar_usuario_existe(usuario_id)

        # Premisas ya validadas: dan la deuda a registrar y los días de retraso efectivos
        monto_descuento, dias_retraso = self._premisas_sancion(
            tipo, monto_opcional, dias_retardo
        )

        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)

        if perfil is None:
            perfil = PerfilReputacion.crear_para_usuario(usuario_id)

        antes = perfil.puntaje.puntos
        self._asegurar_saldo_inicial_legacy(perfil)

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
        despues = perfil.puntaje.puntos

        self._registrar_movimiento(
            usuario_id=usuario_id,
            tipo=TipoMovimientoReputacion.SANCION,
            motivo=motivo,
            puntaje_anterior=antes,
            puntaje_resultante=despues,
            fecha_movimiento=fecha_aplicacion,
            sancion_id=sancion.id,
            prestamo_id=prestamo_id,
            reserva_id=reserva_id,
            recurso_id=recurso_id,
            recurso_nombre=recurso_nombre,
        )

        return SancionDTO.from_entity(sancion)

    def premiar_devolucion_puntual(
        self,
        usuario_id: UUID,
        *,
        prestamo_id: UUID | None = None,
        reserva_id: UUID | None = None,
        recurso_id: UUID | None = None,
        recurso_nombre: str | None = None,
    ) -> None:
        """
        Premia la devolución puntual de un usuario (RF-10).

        - RF-23: verifica que el usuario exista antes de operar (sin perfiles huérfanos)
        - Autocrea el perfil (500, NORMAL) si no existe → el premio lo deja en 510
        - Suma 10 puntos con tope 1000, recalcula el nivel y persiste
        """
        self._premiar_puntualidad(
            usuario_id,
            TipoMovimientoReputacion.BONIFICACION_DEVOLUCION_PUNTUAL,
            "Devolución puntual",
            prestamo_id=prestamo_id,
            reserva_id=reserva_id,
            recurso_id=recurso_id,
            recurso_nombre=recurso_nombre,
        )

    def premiar_entrega_puntual(
        self,
        usuario_id: UUID,
        *,
        prestamo_id: UUID | None = None,
        reserva_id: UUID | None = None,
        recurso_id: UUID | None = None,
        recurso_nombre: str | None = None,
    ) -> None:
        """Aplica la bonificación de puntualidad definida para entregas a tiempo."""
        self._premiar_puntualidad(
            usuario_id,
            TipoMovimientoReputacion.BONIFICACION_ENTREGA_PUNTUAL,
            "Entrega puntual",
            prestamo_id=prestamo_id,
            reserva_id=reserva_id,
            recurso_id=recurso_id,
            recurso_nombre=recurso_nombre,
        )

    def ejecutar_amnistia_mensual(self) -> int:
        """
        Ejecuta la amnistía mensual y devuelve cuántos perfiles premió (RF-11, RF-13).

        - Recorre solo los perfiles en nivel BAJO (RF-12: otros niveles no reciben amnistía)
        - La regla de los 30 días vive en el dominio (`aplicar_amnistia`); 0 premiados
          es un resultado válido
        - Persiste cada perfil premiado (con su nivel recalculado) y registra bitácora
        """
        perfiles_bajos = self._perfil_reputacion_repository.obtener_por_nivel(
            NivelReputacion.BAJO
        )

        perfiles_premiados = 0
        for perfil in perfiles_bajos:
            antes = perfil.puntaje.puntos
            fecha_antes = perfil.fecha_actualizacion
            if perfil.aplicar_amnistia():
                self._asegurar_saldo_inicial_legacy(
                    perfil,
                    puntaje_anterior=antes,
                    fecha_referencia=fecha_antes,
                )
                self._perfil_reputacion_repository.guardar(perfil)
                despues = perfil.puntaje.puntos
                self._registrar_movimiento(
                    usuario_id=perfil.usuario_id,
                    tipo=TipoMovimientoReputacion.AMNISTIA_MENSUAL,
                    motivo="Amnistía mensual",
                    puntaje_anterior=antes,
                    puntaje_resultante=despues,
                )
                perfiles_premiados += 1

        return perfiles_premiados

    def listar_movimientos_usuario(self, usuario_id: UUID) -> list[MovimientoReputacionDTO]:
        """Consulta la bitácora cronológica de un usuario (del más reciente al más antiguo)."""
        self._verificar_usuario_existe(usuario_id)
        movimientos = self._obtener_movimientos_usuario_entidades(usuario_id)
        return [MovimientoReputacionDTO.from_entity(m) for m in movimientos]

    def exportar_csv_usuario(self, usuario_id: UUID) -> tuple[str, str]:
        """Genera el CSV UTF-8 (con BOM) de movimientos de reputación de un usuario."""
        usuario = self._usuario_repository.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado("Usuario no encontrado")

        movimientos = self._obtener_movimientos_usuario_entidades(usuario_id)
        filas: list[tuple[Usuario | None, MovimientoReputacion]] = [
            (usuario, mov) for mov in movimientos
        ]
        return f"movimientos_reputacion_{usuario_id}.csv", self._generar_csv(filas)

    def exportar_csv_global(self) -> tuple[str, str]:
        """Genera el CSV UTF-8 (con BOM) global de movimientos de todos los usuarios."""
        usuarios = self._usuario_repository.listar()
        usuarios_por_id = {u.id: u for u in usuarios}

        movimientos = (
            list(self._movimiento_reputacion_repository.obtener_todos())
            if self._movimiento_reputacion_repository is not None
            else []
        )
        usuarios_con_movimientos = {m.usuario_id for m in movimientos}

        for usuario in usuarios:
            if usuario.id in usuarios_con_movimientos:
                continue
            perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario.id)
            if perfil is not None and perfil.puntaje.puntos != 500:
                movimientos.append(self._crear_movimiento_saldo_heredado(perfil))

        movimientos_ordenados = sorted(
            movimientos,
            key=lambda m: (self._normalizar_utc(m.fecha_movimiento), m.numero_secuencia),
            reverse=True,
        )
        filas: list[tuple[Usuario | None, MovimientoReputacion]] = [
            (
                usuarios_por_id.get(m.usuario_id)
                or self._usuario_repository.obtener_por_id(m.usuario_id),
                m,
            )
            for m in movimientos_ordenados
        ]
        return "movimientos_reputacion_global.csv", self._generar_csv(filas)

    def _premiar_puntualidad(
        self,
        usuario_id: UUID,
        tipo: TipoMovimientoReputacion,
        motivo: str,
        *,
        prestamo_id: UUID | None = None,
        reserva_id: UUID | None = None,
        recurso_id: UUID | None = None,
        recurso_nombre: str | None = None,
    ) -> None:
        """Aplica bonificación por puntualidad (+10, tope 1000) y registra su movimiento."""
        self._verificar_usuario_existe(usuario_id)

        perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)

        if perfil is None:
            perfil = PerfilReputacion.crear_para_usuario(usuario_id)

        antes = perfil.puntaje.puntos
        self._asegurar_saldo_inicial_legacy(perfil)
        perfil.premiar_puntualidad()
        self._perfil_reputacion_repository.guardar(perfil)
        despues = perfil.puntaje.puntos

        self._registrar_movimiento(
            usuario_id=usuario_id,
            tipo=tipo,
            motivo=motivo,
            puntaje_anterior=antes,
            puntaje_resultante=despues,
            prestamo_id=prestamo_id,
            reserva_id=reserva_id,
            recurso_id=recurso_id,
            recurso_nombre=recurso_nombre,
        )

    def _asegurar_saldo_inicial_legacy(
        self,
        perfil: PerfilReputacion,
        *,
        puntaje_anterior: int | None = None,
        fecha_referencia: datetime | None = None,
    ) -> None:
        """Persiste una sola vez el saldo heredado de perfiles previos distintos de 500."""
        if self._movimiento_reputacion_repository is None:
            return
        puntos = perfil.puntaje.puntos if puntaje_anterior is None else puntaje_anterior
        if puntos == 500:
            return
        if self._movimiento_reputacion_repository.contar_por_usuario(perfil.usuario_id) != 0:
            return
        movimiento = self._crear_movimiento_saldo_heredado(
            perfil,
            puntaje_anterior=puntos,
            fecha_referencia=fecha_referencia,
        )
        self._movimiento_reputacion_repository.registrar(movimiento)

    @classmethod
    def _crear_movimiento_saldo_heredado(
        cls,
        perfil: PerfilReputacion,
        *,
        puntaje_anterior: int | None = None,
        fecha_referencia: datetime | None = None,
    ) -> MovimientoReputacion:
        """Construye la entidad SALDO_INICIAL_HEREDADO sin efectos secundarios."""
        puntos = perfil.puntaje.puntos if puntaje_anterior is None else puntaje_anterior
        fecha_base = perfil.fecha_actualizacion if fecha_referencia is None else fecha_referencia
        return MovimientoReputacion(
            usuario_id=perfil.usuario_id,
            tipo=TipoMovimientoReputacion.SALDO_INICIAL_HEREDADO,
            motivo="Saldo previo a bitácora",
            puntaje_anterior=500,
            variacion_puntos=puntos - 500,
            puntaje_resultante=puntos,
            fecha_movimiento=cls._normalizar_utc(fecha_base),
            numero_secuencia=1,
        )

    def _registrar_movimiento(
        self,
        *,
        usuario_id: UUID,
        tipo: TipoMovimientoReputacion,
        motivo: str,
        puntaje_anterior: int,
        puntaje_resultante: int,
        fecha_movimiento: datetime | None = None,
        sancion_id: UUID | None = None,
        prestamo_id: UUID | None = None,
        reserva_id: UUID | None = None,
        recurso_id: UUID | None = None,
        recurso_nombre: str | None = None,
    ) -> None:
        """Registra un movimiento en la bitácora si el repositorio está disponible."""
        if self._movimiento_reputacion_repository is None:
            return
        secuencia = self._movimiento_reputacion_repository.obtener_siguiente_secuencia(usuario_id)
        fecha = (
            self._normalizar_utc(fecha_movimiento)
            if fecha_movimiento is not None
            else datetime.now(UTC)
        )
        movimiento = MovimientoReputacion(
            usuario_id=usuario_id,
            tipo=tipo,
            motivo=motivo,
            puntaje_anterior=puntaje_anterior,
            variacion_puntos=puntaje_resultante - puntaje_anterior,
            puntaje_resultante=puntaje_resultante,
            fecha_movimiento=fecha,
            numero_secuencia=secuencia,
            sancion_id=sancion_id,
            prestamo_id=prestamo_id,
            reserva_id=reserva_id,
            recurso_id=recurso_id,
            recurso_nombre=recurso_nombre,
        )
        self._movimiento_reputacion_repository.registrar(movimiento)

    def _obtener_movimientos_usuario_entidades(
        self, usuario_id: UUID
    ) -> list[MovimientoReputacion]:
        """Obtiene movimientos persistidos o saldo heredado virtual en memoria (solo lectura)."""
        movimientos = (
            list(self._movimiento_reputacion_repository.obtener_por_usuario(usuario_id))
            if self._movimiento_reputacion_repository is not None
            else []
        )
        if not movimientos:
            perfil = self._perfil_reputacion_repository.obtener_por_usuario(usuario_id)
            if perfil is not None and perfil.puntaje.puntos != 500:
                return [self._crear_movimiento_saldo_heredado(perfil)]
        return sorted(
            movimientos,
            key=lambda m: (self._normalizar_utc(m.fecha_movimiento), m.numero_secuencia),
            reverse=True,
        )

    @staticmethod
    def _normalizar_utc(fecha: datetime) -> datetime:
        """Asegura fecha UTC aware (SQLite puede devolver datetimes naive)."""
        if fecha.tzinfo is None:
            return fecha.replace(tzinfo=UTC)
        return fecha.astimezone(UTC)

    @staticmethod
    def _sanear_celda_csv(valor: str | None) -> str:
        """Neutraliza inyección de fórmulas en celdas de texto libre CSV."""
        if not valor:
            return ""
        if valor.startswith(_PREFIJOS_FORMULA_CSV) or valor.lstrip(" ").startswith(
            _PREFIJOS_FORMULA_CSV
        ):
            return f"'{valor}"
        return valor

    def _generar_csv(self, filas: list[tuple[Usuario | None, MovimientoReputacion]]) -> str:
        """Serializa filas de movimientos en CSV UTF-8 con BOM y protección anti-fórmulas."""
        buffer = io.StringIO(newline="")
        buffer.write("\ufeff")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(list(_COLUMNAS_CSV))
        for usuario, mov in filas:
            nombre_usuario = usuario.nombre if usuario is not None else str(mov.usuario_id)
            correo_usuario = usuario.correo if usuario is not None else ""
            writer.writerow(
                [
                    self._sanear_celda_csv(nombre_usuario),
                    self._sanear_celda_csv(correo_usuario),
                    self._normalizar_utc(mov.fecha_movimiento).isoformat(),
                    self._sanear_celda_csv(mov.tipo.value),
                    self._sanear_celda_csv(mov.motivo),
                    self._sanear_celda_csv(mov.recurso_nombre),
                    mov.puntaje_anterior,
                    mov.variacion_puntos,
                    mov.puntaje_resultante,
                ]
            )
        return buffer.getvalue()

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