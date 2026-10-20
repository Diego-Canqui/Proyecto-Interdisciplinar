"""Tests para los DTOs de reputación: PerfilReputacionDTO, SancionDTO, ExcepcionAcademicaDTO."""
import pytest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from pydantic import ValidationError

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import PerfilReputacion
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.excepcion_academica import ExcepcionAcademica
from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import PuntajeReputacion


@pytest.mark.unit
class TestSancionDTO:
    """Tests para SancionDTO."""

    def test_campos_completos(self):
        """SancionDTO debe tener todos los campos requeridos (incluidos fecha_fin y vigente)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import SancionDTO

        id_val = uuid4()
        ahora = datetime.now(UTC)
        dto = SancionDTO(
            id=id_val,
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Devolución tardía",
            fecha_aplicacion=ahora,
            fecha_fin=ahora + timedelta(days=2),
            activa=True,
            vigente=True,
        )

        assert dto.id == id_val
        assert dto.tipo == TipoSancion.TARDANZA
        assert dto.puntos_descuento == -10
        assert dto.monto_descuento == Decimal("0")
        assert dto.motivo == "Devolución tardía"
        assert dto.fecha_aplicacion is not None
        assert dto.fecha_fin == ahora + timedelta(days=2)
        assert dto.activa is True
        assert dto.vigente is True

    def test_from_entity(self):
        """from_entity() debe crear SancionDTO desde entidad Sancion, con fecha_fin y vigencia derivada."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import SancionDTO

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=datetime.now(UTC),
            fecha_fin=datetime.now(UTC) + timedelta(days=30),
            activa=True,
        )

        dto = SancionDTO.from_entity(sancion)

        assert dto.id == sancion.id
        assert dto.tipo == sancion.tipo
        assert dto.puntos_descuento == sancion.puntos_descuento
        assert dto.monto_descuento == sancion.monto_descuento
        assert dto.motivo == sancion.motivo
        assert dto.fecha_aplicacion == sancion.fecha_aplicacion
        assert dto.fecha_fin == sancion.fecha_fin
        assert dto.activa == sancion.activa
        assert dto.vigente is True

    def test_from_entity_sancion_expirada_vigente_false(self):
        """from_entity() debe derivar vigente=False para una sanción expirada."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import SancionDTO

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

        dto = SancionDTO.from_entity(sancion)

        assert dto.fecha_fin == sancion.fecha_fin
        assert dto.vigente is False

    def test_from_attributes_config(self):
        """SancionDTO debe tener from_attributes=True en model_config."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import SancionDTO

        assert SancionDTO.model_config.get("from_attributes") is True


@pytest.mark.unit
class TestAplicarSancionDTO:
    """Tests para la validación por tipo de AplicarSancionDTO (RF-06, RF-07 → 422)."""

    def test_acepta_tardanza_con_dias_retardo_1(self):
        """TARDANZA con dias_retardo=1 (gracia) debe ser válida."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        dto = AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.TARDANZA, motivo="Retraso de 1 día", dias_retardo=1)

        assert dto.dias_retardo == 1
        assert dto.monto_opcional is None

    def test_acepta_tardanza_con_dias_retardo_5(self):
        """TARDANZA con dias_retardo=5 debe ser válida (bloqueo 1:1)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        dto = AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.TARDANZA, motivo="Retraso de 5 días", dias_retardo=5)

        assert dto.dias_retardo == 5

    def test_rechaza_tardanza_sin_dias_retardo(self):
        """TARDANZA exige dias_retardo: ausente → ValidationError (RF-07)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        with pytest.raises(ValidationError):
            AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.TARDANZA, motivo="Tardanza sin retraso")

    def test_rechaza_tardanza_con_dias_retardo_cero(self):
        """TARDANZA con dias_retardo=0 → ValidationError: un usuario puntual no se sanciona (RF-07)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        with pytest.raises(ValidationError):
            AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.TARDANZA, motivo="Retraso nulo", dias_retardo=0)

    def test_rechaza_tardanza_con_dias_retardo_negativo(self):
        """TARDANZA con dias_retardo negativo → ValidationError (RF-07)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        with pytest.raises(ValidationError):
            AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.TARDANZA, motivo="Retraso negativo", dias_retardo=-3)

    def test_acepta_dano_total_con_monto(self):
        """DANO_TOTAL con monto_opcional=350 debe ser válido."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        dto = AplicarSancionDTO(
            usuario_id=uuid4(),
            tipo=TipoSancion.DANO_TOTAL,
            motivo="Recurso destruido",
            monto_opcional=Decimal("350"),
        )

        assert dto.monto_opcional == Decimal("350")
        assert dto.dias_retardo is None

    def test_rechaza_dano_total_sin_monto(self):
        """DANO_TOTAL sin monto_opcional → ValidationError (RF-06: la deuda no puede ser $0)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        with pytest.raises(ValidationError):
            AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.DANO_TOTAL, motivo="Recurso destruido")

    def test_rechaza_dano_total_con_monto_cero(self):
        """DANO_TOTAL con monto_opcional=0 → ValidationError (RF-06)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        with pytest.raises(ValidationError):
            AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.DANO_TOTAL, motivo="Recurso destruido", monto_opcional=0)

    def test_rechaza_dano_total_con_monto_negativo(self):
        """DANO_TOTAL con monto_opcional negativo → ValidationError (RF-06)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        with pytest.raises(ValidationError):
            AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.DANO_TOTAL, motivo="Recurso destruido", monto_opcional=Decimal("-10"))

    def test_acepta_dano_parcial_ignorando_extras(self):
        """RF-06/RF-07: DANO_PARCIAL ignora monto y dias_retardo recibidos (deuda y bloqueo fijos)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        dto = AplicarSancionDTO(
            usuario_id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            motivo="Daño parcial",
            monto_opcional=Decimal("999"),
            dias_retardo=9,
        )

        # Los extras se conservan en el DTO pero no generan error: el servicio los ignora
        assert dto.tipo == TipoSancion.DANO_PARCIAL

    def test_acepta_inasistencia_sin_extras(self):
        """INASISTENCIA_RESERVA sin extras debe ser válida (bloqueo fijo)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import AplicarSancionDTO

        dto = AplicarSancionDTO(usuario_id=uuid4(), tipo=TipoSancion.INASISTENCIA_RESERVA, motivo="No recogió la reserva")

        assert dto.monto_opcional is None
        assert dto.dias_retardo is None


@pytest.mark.unit
class TestExcepcionAcademicaDTO:
    """Tests para ExcepcionAcademicaDTO."""

    def test_campos_completos(self):
        """ExcepcionAcademicaDTO debe tener todos los campos requeridos."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import ExcepcionAcademicaDTO

        id_val = uuid4()
        usuario_id = uuid4()
        ahora = datetime.now(UTC)

        dto = ExcepcionAcademicaDTO(
            id=id_val,
            usuario_id=usuario_id,
            motivo="Examen final",
            fecha_inicio=ahora,
            fecha_fin=ahora,
            activa=True,
        )

        assert dto.id == id_val
        assert dto.usuario_id == usuario_id
        assert dto.motivo == "Examen final"
        assert dto.fecha_inicio == ahora
        assert dto.fecha_fin == ahora
        assert dto.activa is True

    def test_from_entity(self):
        """from_entity() debe crear ExcepcionAcademicaDTO desde entidad ExcepcionAcademica."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import ExcepcionAcademicaDTO

        excepcion = ExcepcionAcademica(
            id=uuid4(),
            usuario_id=uuid4(),
            motivo="Examen",
            fecha_inicio=datetime.now(UTC),
            fecha_fin=datetime.now(UTC),
            activa=True,
        )

        dto = ExcepcionAcademicaDTO.from_entity(excepcion)

        assert dto.id == excepcion.id
        assert dto.usuario_id == excepcion.usuario_id
        assert dto.motivo == excepcion.motivo
        assert dto.fecha_inicio == excepcion.fecha_inicio
        assert dto.fecha_fin == excepcion.fecha_fin
        assert dto.activa == excepcion.activa

    def test_from_attributes_config(self):
        """ExcepcionAcademicaDTO debe tener from_attributes=True en model_config."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import ExcepcionAcademicaDTO

        assert ExcepcionAcademicaDTO.model_config.get("from_attributes") is True


@pytest.mark.unit
class TestPerfilReputacionDTO:
    """Tests para PerfilReputacionDTO."""

    def test_campos_completos(self):
        """PerfilReputacionDTO debe tener todos los campos requeridos incluyendo lista de sanciones."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import PerfilReputacionDTO, SancionDTO

        id_val = uuid4()
        usuario_id = uuid4()
        ahora = datetime.now(UTC)
        sanciones = [
            SancionDTO(
                id=uuid4(),
                tipo=TipoSancion.TARDANZA,
                puntos_descuento=-10,
                monto_descuento=Decimal("0"),
                motivo="Tardanza",
                fecha_aplicacion=ahora,
                fecha_fin=ahora + timedelta(days=2),
                activa=True,
                vigente=True,
            )
        ]

        dto = PerfilReputacionDTO(
            id=id_val,
            usuario_id=usuario_id,
            puntaje=500,
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=ahora,
            sanciones=sanciones,
        )

        assert dto.id == id_val
        assert dto.usuario_id == usuario_id
        assert dto.puntaje == 500
        assert dto.nivel == NivelReputacion.NORMAL
        assert dto.fecha_actualizacion == ahora
        assert dto.sanciones == sanciones
        assert len(dto.sanciones) == 1

    def test_from_entity(self):
        """from_entity() debe crear PerfilReputacionDTO desde entidad PerfilReputacion con sanciones."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import PerfilReputacionDTO

        usuario_id = uuid4()
        ahora = datetime.now(UTC)

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=usuario_id,
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=ahora,
            sanciones=[
                Sancion(
                    id=uuid4(),
                    tipo=TipoSancion.TARDANZA,
                    puntos_descuento=-10,
                    monto_descuento=Decimal("0"),
                    motivo="Tardanza",
                    fecha_aplicacion=ahora,
                    fecha_fin=ahora + timedelta(days=2),
                    activa=True,
                ),
                Sancion(
                    id=uuid4(),
                    tipo=TipoSancion.DANO_PARCIAL,
                    puntos_descuento=-30,
                    monto_descuento=Decimal("50"),
                    motivo="Daño parcial",
                    fecha_aplicacion=ahora,
                    fecha_fin=ahora + timedelta(days=30),
                    activa=False,
                ),
            ],
        )

        dto = PerfilReputacionDTO.from_entity(perfil)

        assert dto.id == perfil.id
        assert dto.usuario_id == perfil.usuario_id
        assert dto.puntaje == perfil.puntaje.puntos
        assert dto.nivel == perfil.nivel
        assert dto.fecha_actualizacion == perfil.fecha_actualizacion
        assert len(dto.sanciones) == 2

        # Verificar primera sanción (activa y no expirada → vigente)
        s1 = dto.sanciones[0]
        assert s1.tipo == TipoSancion.TARDANZA
        assert s1.puntos_descuento == -10
        assert s1.monto_descuento == Decimal("0")
        assert s1.motivo == "Tardanza"
        assert s1.activa is True
        assert s1.fecha_fin == ahora + timedelta(days=2)
        assert s1.vigente is True

        # Verificar segunda sanción (inactiva → no vigente)
        s2 = dto.sanciones[1]
        assert s2.tipo == TipoSancion.DANO_PARCIAL
        assert s2.puntos_descuento == -30
        assert s2.monto_descuento == Decimal("50")
        assert s2.motivo == "Daño parcial"
        assert s2.activa is False
        assert s2.fecha_fin == ahora + timedelta(days=30)
        assert s2.vigente is False

    def test_from_entity_sin_sanciones(self):
        """from_entity() debe funcionar con lista de sanciones vacía."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import PerfilReputacionDTO

        usuario_id = uuid4()
        ahora = datetime.now(UTC)

        perfil = PerfilReputacion(
            id=uuid4(),
            usuario_id=usuario_id,
            puntaje=PuntajeReputacion(puntos=500),
            nivel=NivelReputacion.NORMAL,
            fecha_actualizacion=ahora,
            sanciones=[],
        )

        dto = PerfilReputacionDTO.from_entity(perfil)

        assert dto.id == perfil.id
        assert dto.usuario_id == perfil.usuario_id
        assert dto.puntaje == 500
        assert dto.nivel == NivelReputacion.NORMAL
        assert dto.sanciones == []

    def test_from_attributes_config(self):
        """PerfilReputacionDTO debe tener from_attributes=True en model_config."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import PerfilReputacionDTO

        assert PerfilReputacionDTO.model_config.get("from_attributes") is True


@pytest.mark.unit
class TestElegibilidadDTO:
    """Tests para ElegibilidadDTO (GET /reputacion/elegibilidad, RF-21)."""

    def test_con_razon_si_no_elegible(self):
        """ElegibilidadDTO debe llevar la razón en lenguaje de negocio si no es elegible."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import ElegibilidadDTO

        razon = "tienes una sanción vigente de tipo DANO_PARCIAL hasta 2026-11-30"
        dto = ElegibilidadDTO(elegible=False, razon=razon)

        assert dto.elegible is False
        assert dto.razon == razon

    def test_sin_razon_si_elegible(self):
        """ElegibilidadDTO: si es elegible, la razón es None (por defecto)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import ElegibilidadDTO

        dto = ElegibilidadDTO(elegible=True)

        assert dto.elegible is True
        assert dto.razon is None


@pytest.mark.unit
class TestResultadoAmnistiaDTO:
    """Tests para ResultadoAmnistiaDTO (POST /reputacion/amnistia, RF-13)."""

    def test_con_conteo_positivo(self):
        """ResultadoAmnistiaDTO debe llevar la cantidad de perfiles premiados."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import ResultadoAmnistiaDTO

        dto = ResultadoAmnistiaDTO(perfiles_premiados=3)

        assert dto.perfiles_premiados == 3

    def test_con_cero_premiados(self):
        """ResultadoAmnistiaDTO: 0 premiados es un resultado válido, no un error (RF-13)."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import ResultadoAmnistiaDTO

        dto = ResultadoAmnistiaDTO(perfiles_premiados=0)

        assert dto.perfiles_premiados == 0


@pytest.mark.unit
class TestDTOsExports:
    """Tests para verificar que los DTOs se exportan correctamente."""

    def test_imports_desde_modulo_dto(self):
        """Los 5 DTOs de reputación deben ser importables desde el módulo dto."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto import (
            PerfilReputacionDTO,
            SancionDTO,
            ExcepcionAcademicaDTO,
            ElegibilidadDTO,
            ResultadoAmnistiaDTO,
        )

        assert PerfilReputacionDTO is not None
        assert SancionDTO is not None
        assert ExcepcionAcademicaDTO is not None
        assert ElegibilidadDTO is not None
        assert ResultadoAmnistiaDTO is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])