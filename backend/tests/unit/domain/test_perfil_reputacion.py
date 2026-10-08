"""Tests para la entidad PerfilReputacion (Aggregate Root)."""
import pytest
from datetime import datetime, timedelta
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
            activa=False,
        )

        perfil.aplicar_sancion(sancion)

        # 305 - 30 = 275 -> BAJO
        assert perfil.puntaje.puntos == 275
        assert perfil.nivel == NivelReputacion.BAJO

    def test_es_elegible_falso_si_nivel_bajo(self):
        """es_elegible_para_prestamo() debe ser False si nivel == BAJO."""
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

        assert perfil.es_elegible_para_prestamo([]) is False

    def test_es_elegible_falso_si_sancion_activa_bloqueante_sin_excepcion(self):
        """es_elegible_para_prestamo() debe ser False si hay sanción activa y no hay excepción que cubra."""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])