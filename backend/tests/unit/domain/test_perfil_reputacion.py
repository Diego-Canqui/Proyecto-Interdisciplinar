"""Tests para la entidad PerfilReputacion (Aggregate Root)."""
import pytest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion


@pytest.mark.unit
class TestPerfilReputacion:
    """Tests para PerfilReputacion (Aggregate Root)."""

    def test_factory_crear_para_usuario_inicializa_con_500_normal(self):
        """crear_para_usuario() debe crear perfil con puntaje 500 (NORMAL) y sanciones vacías."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        usuario_id = uuid4()
        perfil = PerfilReputacion.crear_para_usuario(usuario_id)

        assert perfil.usuario_id == usuario_id
        assert isinstance(perfil.puntaje, PuntajeReputacion)
        assert perfil.puntaje.puntos == 500
        assert perfil.nivel == NivelReputacion.NORMAL
        assert perfil.sanciones == []
        assert perfil.fecha_actualizacion is not None

    def test_recalcular_nivel_umbral_bajo(self):
        """recalcular_nivel() debe poner BAJO para 0-299 puntos."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=200),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
        )

        nivel = perfil.recalcular_nivel()

        assert nivel == NivelReputacion.BAJO
        assert perfil.nivel == NivelReputacion.BAJO
        assert perfil.fecha_actualizacion is not None

    def test_recalcular_nivel_umbral_normal(self):
        """recalcular_nivel() debe poner NORMAL para 300-599 puntos."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=450),
            nivel=NivelReputacion.BAJO,
            fecha_actualizacion=datetime.now(),
        )

        nivel = perfil.recalcular_nivel()

        assert nivel == NivelReputacion.NORMAL
        assert perfil.nivel == NivelReputacion.NORMAL

    def test_recalcular_nivel_umbral_bueno(self):
        """recalcular_nivel() debe poner BUENO para 600-799 puntos."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=700),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
        )

        nivel = perfil.recalcular_nivel()

        assert nivel == NivelReputacion.BUENO
        assert perfil.nivel == NivelReputacion.BUENO

    def test_recalcular_nivel_umbral_excelente(self):
        """recalcular_nivel() debe poner EXCELENTE para 800-1000 puntos."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=900),
            nivel=NivelReputacion.BUENO,
            fecha_actualizacion=datetime.now(),
        )

        nivel = perfil.recalcular_nivel()

        assert nivel == NivelReputacion.EXCELENTE
        assert perfil.nivel == NivelReputacion.EXCELENTE

    def test_aplicar_sancion_anade_a_lista_llama_aplicar_descuenta_y_recalcula(self):
        """aplicar_sancion() debe añadir sanción, llamr s.aplicar(), descontar puntos y recalcular nivel."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
        )

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=datetime.now(),
            fecha_fin=datetime.now(UTC) + timedelta(days=2),
            activa=False,
        )

        perfil.aplicar_sancion(sancion)

        # Sanción añadida a la lista
        assert len(perfil.sanciones) == 1
        assert perfil.sanciones[0] is sancion

        # Sanción marcada como activa
        assert sancion.activa is True

        # Puntos descontados (500 - 10 = 490)
        assert perfil.puntaje.puntos == 490

        # Nivel recalculado (490 sigue siendo NORMAL)
        assert perfil.nivel == NivelReputacion.NORMAL

    def test_aplicar_sancion_recalcula_nivel_si_baja(self):
        """aplicar_sancion() debe recalcular nivel si la sanción lo hace bajar."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=305),  # NORMAL (300-599)
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
        )

        # Sanción de -30 puntos (DANO_PARCIAL)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=datetime.now(),
            fecha_fin=datetime.now(UTC) + timedelta(days=30),
            activa=False,
        )

        perfil.aplicar_sancion(sancion)

        # 305 - 30 = 275 -> BAJO
        assert perfil.puntaje.puntos == 275
        assert perfil.nivel == NivelReputacion.BAJO

    def test_es_elegible_verdadero_si_nivel_bajo_sin_sanciones_vigentes(self):
        """RF-01 (deroga RF-19 de spec 001): nivel BAJO sin sanciones vigentes → elegible."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=200),
            nivel=NivelReputacion.BAJO,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        assert perfil.es_elegible_para_prestamo([]) is True

    def test_es_elegible_falso_si_sancion_activa_bloqueante_sin_excepcion(self):
        """es_elegible_para_prestamo() debe ser False si hay sanción vigente no cubierta (RF-02)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=datetime.now(),
            fecha_fin=datetime.now(UTC) + timedelta(days=2),  # vigente
            activa=True,
        )
        perfil.sanciones.append(sancion)

        assert perfil.es_elegible_para_prestamo([]) is False

    def test_es_elegible_verdadero_si_excepcion_cubre_sancion(self):
        """es_elegible_para_prestamo() debe ser True si hay excepción vigente que cubre la sanción."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=datetime.now(),
            fecha_fin=datetime.now(UTC) + timedelta(days=2),  # vigente
            activa=True,
        )
        perfil.sanciones.append(sancion)

        # Excepción vigente que cubre TARDANZA
        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=perfil.usuario_id,
            motivo="Examen",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )

        assert perfil.es_elegible_para_prestamo([excepcion]) is True

    def test_es_elegible_verdadero_si_nivel_normal_sin_sanciones_bloqueantes(self):
        """es_elegible_para_prestamo() debe ser True si nivel >= NORMAL y sin sanciones bloqueantes."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        assert perfil.es_elegible_para_prestamo([]) is True

    def test_es_elegible_sancion_inactiva_no_bloquea(self):
        """Sanción inactiva no debe bloquear elegibilidad."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_TOTAL,
            puntos_descuento=-100,
            monto_descuento=Decimal("0"),
            motivo="Daño total",
            fecha_aplicacion=datetime.now(),
            fecha_fin=datetime.now(UTC) + timedelta(days=60),  # futura: prueba que la inactiva no bloquea aunque no haya expirado
            activa=False,  # Inactiva
        )
        perfil.sanciones.append(sancion)

        assert perfil.es_elegible_para_prestamo([]) is True

    def test_es_elegible_excepcion_no_vigente_no_cubre(self):
        """Excepción no vigente (fuera de fechas o inactiva) no debe cubrir sanción."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=datetime.now(),
            fecha_fin=datetime.now(UTC) + timedelta(days=2),  # vigente
            activa=True,
        )
        perfil.sanciones.append(sancion)

        # Excepción expirada
        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=perfil.usuario_id,
            motivo="Examen pasado",
            fecha_inicio=ahora - timedelta(days=10),
            fecha_fin=ahora - timedelta(days=5),
            activa=True,
        )

        assert perfil.es_elegible_para_prestamo([excepcion]) is False

    def test_es_elegible_excepcion_inactiva_no_cubre(self):
        """Excepción inactiva no debe cubrir sanción aunque fechas sean correctas."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=datetime.now(),
            fecha_fin=datetime.now(UTC) + timedelta(days=2),  # vigente
            activa=True,
        )
        perfil.sanciones.append(sancion)

        # Excepción inactiva
        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=perfil.usuario_id,
            motivo="Examen",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=False,  # Inactiva
        )

        assert perfil.es_elegible_para_prestamo([excepcion]) is False

    def test_es_elegible_verdadero_si_sancion_expirada_aun_con_nivel_bajo(self):
        """RF-01/RF-02 (caso límite 6): sanción expirada no bloquea aunque el nivel sea BAJO."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=200),  # Nivel BAJO
            nivel=NivelReputacion.BAJO,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        # Sanción activa pero expirada (fecha_fin ya pasó)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza antigua",
            fecha_aplicacion=datetime.now(UTC) - timedelta(days=10),
            fecha_fin=datetime.now(UTC) - timedelta(seconds=1),
            activa=True,
        )
        perfil.sanciones.append(sancion)

        assert perfil.es_elegible_para_prestamo([]) is True

    def test_excepcion_vigente_cubre_inasistencia_reserva(self):
        """RF-15: excepción vigente cubre sanción vigente de INASISTENCIA_RESERVA."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.INASISTENCIA_RESERVA,
            puntos_descuento=-15,
            monto_descuento=Decimal("0"),
            motivo="No recogió la reserva",
            fecha_aplicacion=datetime.now(UTC),
            fecha_fin=datetime.now(UTC) + timedelta(days=3),
            activa=True,
        )
        perfil.sanciones.append(sancion)

        # Excepción vigente que cubre INASISTENCIA_RESERVA
        ahora = datetime.now(UTC)
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=perfil.usuario_id,
            motivo="Justificación médica",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )

        assert perfil.es_elegible_para_prestamo([excepcion]) is True

    def test_excepcion_vigente_no_cubre_danos(self):
        """RF-15 (caso límite 13): la cobertura nunca alcanza DANO_PARCIAL ni DANO_TOTAL."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        ahora = datetime.now(UTC)
        sancion_parcial = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=30),
            activa=True,
        )
        sancion_total = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_TOTAL,
            puntos_descuento=-100,
            monto_descuento=Decimal("0"),
            motivo="Daño total",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=60),
            activa=True,
        )
        perfil.sanciones.append(sancion_parcial)
        perfil.sanciones.append(sancion_total)

        # Excepción vigente: cubre TARDANZA/INASISTENCIA_RESERVA, pero no los daños
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=perfil.usuario_id,
            motivo="Examen",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )

        assert perfil.es_elegible_para_prestamo([excepcion]) is False
        # La primera sanción bloqueante es el primer daño vigente
        assert perfil.sancion_bloqueante([excepcion]) is sancion_parcial

    def test_sancion_bloqueante_devuelve_primera_vigente_no_cubierta(self):
        """sancion_bloqueante() devuelve la primera sanción vigente no cubierta."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        ahora = datetime.now(UTC)
        # Expirada (aunque activa): no bloquea
        sancion_expirada = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_TOTAL,
            puntos_descuento=-100,
            monto_descuento=Decimal("0"),
            motivo="Daño total antiguo",
            fecha_aplicacion=ahora - timedelta(days=61),
            fecha_fin=ahora - timedelta(days=1),
            activa=True,
        )
        # Primera vigente no cubierta: debe ser la respuesta
        sancion_vigente_uno = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=2),
            activa=True,
        )
        # Segunda vigente no cubierta
        sancion_vigente_dos = Sancion(
            id=uuid4(),
            tipo=TipoSancion.INASISTENCIA_RESERVA,
            puntos_descuento=-15,
            monto_descuento=Decimal("0"),
            motivo="Inasistencia",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=3),
            activa=True,
        )
        perfil.sanciones.append(sancion_expirada)
        perfil.sanciones.append(sancion_vigente_uno)
        perfil.sanciones.append(sancion_vigente_dos)

        assert perfil.sancion_bloqueante([]) is sancion_vigente_uno

    def test_sancion_bloqueante_none_si_cubiertas_o_expiradas(self):
        """sancion_bloqueante() es None si las sanciones están cubiertas o expiradas."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        ahora = datetime.now(UTC)
        # TARDANZA vigente cubierta por la excepción vigente
        sancion_cubierta = Sancion(
            id=uuid4(),
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Tardanza",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=2),
            activa=True,
        )
        # DANO_TOTAL activa pero expirada: no bloquea
        sancion_expirada = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_TOTAL,
            puntos_descuento=-100,
            monto_descuento=Decimal("0"),
            motivo="Daño total antiguo",
            fecha_aplicacion=ahora - timedelta(days=61),
            fecha_fin=ahora - timedelta(days=1),
            activa=True,
        )
        perfil.sanciones.append(sancion_cubierta)
        perfil.sanciones.append(sancion_expirada)

        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=perfil.usuario_id,
            motivo="Examen",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )

        assert perfil.sancion_bloqueante([excepcion]) is None
        assert perfil.es_elegible_para_prestamo([excepcion]) is True

    def test_sancion_bloqueante_none_sin_sanciones(self):
        """sancion_bloqueante() es None si el perfil no tiene sanciones."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=uuid4(),
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=datetime.now(),
            sanciones=[],
        )

        assert perfil.sancion_bloqueante([]) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])