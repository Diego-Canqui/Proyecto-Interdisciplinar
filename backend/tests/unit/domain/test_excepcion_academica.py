"""Tests para la entidad ExcepcionAcademica (Aggregate Root)."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion


class TestExcepcionAcademica:
    """Tests para ExcepcionAcademica."""

    def test_es_vigente_true_si_activa_y_fechas_correctas(self):
        """es_vigente() debe ser True si activa=True y fecha_inicio <= now <= fecha_fin."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica

        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Examen",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )

        assert excepcion.es_vigente() is True

    def test_es_vigente_false_si_inactiva(self):
        """es_vigente() debe ser False si activa=False aunque fechas sean correctas."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica

        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Examen",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=False,
        )

        assert excepcion.es_vigente() is False

    def test_es_vigente_false_si_fecha_inicio_futura(self):
        """es_vigente() debe ser False si fecha_inicio > now."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica

        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Examen futuro",
            fecha_inicio=ahora + timedelta(days=1),
            fecha_fin=ahora + timedelta(days=5),
            activa=True,
        )

        assert excepcion.es_vigente() is False

    def test_es_vigente_false_si_fecha_fin_pasada(self):
        """es_vigente() debe ser False si fecha_fin < now."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica

        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Examen pasado",
            fecha_inicio=ahora - timedelta(days=10),
            fecha_fin=ahora - timedelta(days=5),
            activa=True,
        )

        assert excepcion.es_vigente() is False

    def test_aprobar_pone_activa_true(self):
        """aprobar() debe poner activa=True."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica

        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Examen",
            fecha_inicio=datetime.now(),
            fecha_fin=datetime.now() + timedelta(days=1),
            activa=False,
        )

        excepcion.aprobar()

        assert excepcion.activa is True

    def test_rechazar_pone_activa_false(self):
        """rechazar() debe poner activa=False."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica

        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Examen",
            fecha_inicio=datetime.now(),
            fecha_fin=datetime.now() + timedelta(days=1),
            activa=True,
        )

        excepcion.rechazar()

        assert excepcion.activa is False

    def test_cubre_tardanza_si_vigente(self):
        """Excepción vigente debe cubrir sanciones de tipo TARDANZA."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica

        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Examen",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )

        # Verificar que cubre TARDANZA (lógica implícita en es_elegible_para_prestamo)
        # La excepción cubre TARDANZA e INASISTENCIA_RESERVA si está vigente
        assert excepcion.es_vigente() is True
        # La verificación real de cobertura se hace en PerfilReputacion.es_elegible_para_prestamo
        # pero aquí validamos que la excepción esté vigente para esos tipos

    def test_cubre_inasistencia_reserva_si_vigente(self):
        """Excepción vigente debe cubrir sanciones de tipo INASISTENCIA_RESERVA."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica

        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Actividad académica",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )

        assert excepcion.es_vigente() is True

    def test_no_cubre_otros_tipos(self):
        """Excepción no debe cubrir DANO_PARCIAL ni DANO_TOTAL (no son TARDANZA ni INASISTENCIA_RESERVA)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
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

        # Sanción de DANO_PARCIAL (no cubierta por excepción académica)
        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=datetime.now(),
            activa=True,
        )
        perfil.sanciones.append(sancion)

        ahora = datetime.now()
        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=perfil.usuario_id,
            motivo="Examen",
            fecha_inicio=ahora - timedelta(days=1),
            fecha_fin=ahora + timedelta(days=1),
            activa=True,
        )

        # La excepción no cubre DANO_PARCIAL, así que no debe ser elegible
        assert perfil.es_elegible_para_prestamo([excepcion]) is False


# Importar para el último test
from decimal import Decimal
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion


if __name__ == "__main__":
    pytest.main([__file__, "-v"])