"""Tests para los DTOs de reputación: PerfilReputacionDTO, SancionDTO, ExcepcionAcademicaDTO."""
import pytest
from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

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
        """SancionDTO debe tener todos los campos requeridos."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import SancionDTO

        id_val = uuid4()
        dto = SancionDTO(
            id=id_val,
            tipo=TipoSancion.TARDANZA,
            puntos_descuento=-10,
            monto_descuento=Decimal("0"),
            motivo="Devolución tardía",
            fecha_aplicacion=datetime.now(UTC),
            activa=True,
        )

        assert dto.id == id_val
        assert dto.tipo == TipoSancion.TARDANZA
        assert dto.puntos_descuento == -10
        assert dto.monto_descuento == Decimal("0")
        assert dto.motivo == "Devolución tardía"
        assert dto.fecha_aplicacion is not None
        assert dto.activa is True

    def test_from_entity(self):
        """from_entity() debe crear SancionDTO desde entidad Sancion."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import SancionDTO

        sancion = Sancion(
            id=uuid4(),
            tipo=TipoSancion.DANO_PARCIAL,
            puntos_descuento=-30,
            monto_descuento=Decimal("50"),
            motivo="Daño parcial",
            fecha_aplicacion=datetime.now(UTC),
            activa=True,
        )

        dto = SancionDTO.from_entity(sancion)

        assert dto.id == sancion.id
        assert dto.tipo == sancion.tipo
        assert dto.puntos_descuento == sancion.puntos_descuento
        assert dto.monto_descuento == sancion.monto_descuento
        assert dto.motivo == sancion.motivo
        assert dto.fecha_aplicacion == sancion.fecha_aplicacion
        assert dto.activa == sancion.activa

    def test_from_attributes_config(self):
        """SancionDTO debe tener from_attributes=True en model_config."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto.reputacion_dto import SancionDTO

        assert SancionDTO.model_config.get("from_attributes") is True


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
                activa=True,
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
                    activa=True,
                ),
                Sancion(
                    id=uuid4(),
                    tipo=TipoSancion.DANO_PARCIAL,
                    puntos_descuento=-30,
                    monto_descuento=Decimal("50"),
                    motivo="Daño parcial",
                    fecha_aplicacion=ahora,
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

        # Verificar primera sanción
        s1 = dto.sanciones[0]
        assert s1.tipo == TipoSancion.TARDANZA
        assert s1.puntos_descuento == -10
        assert s1.monto_descuento == Decimal("0")
        assert s1.motivo == "Tardanza"
        assert s1.activa is True

        # Verificar segunda sanción
        s2 = dto.sanciones[1]
        assert s2.tipo == TipoSancion.DANO_PARCIAL
        assert s2.puntos_descuento == -30
        assert s2.monto_descuento == Decimal("50")
        assert s2.motivo == "Daño parcial"
        assert s2.activa is False

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


class TestDTOsExports:
    """Tests para verificar que los DTOs se exportan correctamente."""

    def test_imports_desde_modulo_dto(self):
        """Los 3 DTOs deben ser importables desde el módulo dto."""
        from prestamos_recursos.contexts.identidad_reputacion.application.dto import (
            PerfilReputacionDTO,
            SancionDTO,
            ExcepcionAcademicaDTO,
        )

        assert PerfilReputacionDTO is not None
        assert SancionDTO is not None
        assert ExcepcionAcademicaDTO is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])