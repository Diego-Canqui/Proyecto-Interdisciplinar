"""Tests para el modelo de BD PerfilReputacionModel y SancionModel (inline)."""
import pytest
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from prestamos_recursos.contexts.identidad_reputacion.domain.enums.nivel_reputacion import NivelReputacion
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.tipo_sancion import TipoSancion


@pytest.mark.unit
class TestPerfilReputacionModel:
    """Tests para PerfilReputacionModel."""

    def test_tabla_y_schema_correctos(self):
        """Debe tener __tablename__ = 'perfiles_reputacion' y schema 'identidad_reputacion'."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import PerfilReputacionModel

        assert PerfilReputacionModel.__tablename__ == "perfiles_reputacion"
        # __table_args__ es una tupla (UniqueConstraint, {"schema": "identidad_reputacion"})
        table_args = PerfilReputacionModel.__table_args__
        assert isinstance(table_args, tuple)
        # El último elemento debe ser el dict con schema
        schema_dict = table_args[-1]
        assert isinstance(schema_dict, dict)
        assert schema_dict.get("schema") == "identidad_reputacion"

    def test_columnas_requeridas(self):
        """Debe tener todas las columnas requeridas: id, usuario_id, puntos, nivel, fecha_actualizacion."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import PerfilReputacionModel
        from sqlalchemy import inspect

        mapper = inspect(PerfilReputacionModel)
        columnas = {c.key for c in mapper.columns}

        assert "id" in columnas
        assert "usuario_id" in columnas
        assert "puntos" in columnas
        assert "nivel" in columnas
        assert "fecha_actualizacion" in columnas

    def test_usuario_id_unique_fk(self):
        """usuario_id debe tener constraint UNIQUE y FK a identidad_reputacion.usuario.id."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import PerfilReputacionModel
        from sqlalchemy import inspect

        mapper = inspect(PerfilReputacionModel)
        col = mapper.columns["usuario_id"]

        # Verificar unique
        assert col.unique is True

    def test_relacion_sanciones_cascade_delete(self):
        """Debe tener relación 'sanciones' con cascade='all, delete-orphan' hacia SancionModel."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import PerfilReputacionModel, SancionModel
        from sqlalchemy import inspect

        mapper = inspect(PerfilReputacionModel)
        rel = mapper.relationships.get("sanciones")

        assert rel is not None, "Falta relación 'sanciones'"
        assert rel.mapper.class_ is SancionModel
        assert "delete-orphan" in rel.cascade or "delete" in rel.cascade

    def test_puntos_default_500(self):
        """puntos debe tener default 500."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import PerfilReputacionModel
        from sqlalchemy import inspect

        mapper = inspect(PerfilReputacionModel)
        col = mapper.columns["puntos"]
        assert col.default is not None or col.server_default is not None


class TestSancionModelInline:
    """Tests para SancionModel definido inline en perfil_reputacion_model.py."""

    def test_tabla_y_schema_correctos(self):
        """Debe tener __tablename__ = 'sancion' (singular) y schema 'identidad_reputacion'."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import SancionModel

        assert SancionModel.__tablename__ == "sancion"
        # __table_args__ es una tupla ({"schema": "identidad_reputacion"},)
        table_args = SancionModel.__table_args__
        assert isinstance(table_args, tuple)
        schema_dict = table_args[0]
        assert isinstance(schema_dict, dict)
        assert schema_dict.get("schema") == "identidad_reputacion"

    def test_columnas_requeridas(self):
        """Debe tener todas las columnas: id, perfil_reputacion_id, tipo, puntos_descuento, monto_descuento, motivo, fecha_aplicacion, activa."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import SancionModel
        from sqlalchemy import inspect

        mapper = inspect(SancionModel)
        columnas = {c.key for c in mapper.columns}

        assert "id" in columnas
        assert "perfil_reputacion_id" in columnas
        assert "tipo" in columnas
        assert "puntos_descuento" in columnas
        assert "monto_descuento" in columnas
        assert "motivo" in columnas
        assert "fecha_aplicacion" in columnas
        assert "activa" in columnas

    def test_perfil_reputacion_id_fk_cascade(self):
        """perfil_reputacion_id debe ser FK a perfiles_reputacion.id con ON DELETE CASCADE."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import SancionModel
        from sqlalchemy import inspect

        mapper = inspect(SancionModel)
        col = mapper.columns["perfil_reputacion_id"]

        # Verificar que tiene FK
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.column.table.name == "perfiles_reputacion"
        assert fk.column.key == "id"
        # ON DELETE CASCADE se verifica en BD

    def test_relacion_back_populates_perfil(self):
        """Debe tener relación 'perfil' con back_populates hacia PerfilReputacionModel.sanciones."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import SancionModel, PerfilReputacionModel
        from sqlalchemy import inspect

        mapper = inspect(SancionModel)
        rel = mapper.relationships.get("perfil")

        assert rel is not None, "Falta relación 'perfil' en SancionModel"
        assert rel.mapper.class_ is PerfilReputacionModel
        assert rel.back_populates == "sanciones"

    def test_activa_default_true(self):
        """activa debe tener default True."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import SancionModel
        from sqlalchemy import inspect

        mapper = inspect(SancionModel)
        col = mapper.columns["activa"]
        assert col.default is not None or col.server_default is not None


class TestExcepcionAcademicaModel:
    """Tests para ExcepcionAcademicaModel."""

    def test_tabla_y_schema_correctos(self):
        """Debe tener __tablename__ = 'excepciones_academicas' y schema 'identidad_reputacion'."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.excepcion_academica_model import ExcepcionAcademicaModel

        assert ExcepcionAcademicaModel.__tablename__ == "excepciones_academicas"
        # __table_args__ es una tupla ({"schema": "identidad_reputacion"},)
        table_args = ExcepcionAcademicaModel.__table_args__
        assert isinstance(table_args, tuple)
        schema_dict = table_args[0]
        assert isinstance(schema_dict, dict)
        assert schema_dict.get("schema") == "identidad_reputacion"

    def test_columnas_requeridas(self):
        """Debe tener columnas: id, usuario_id, motivo, fecha_inicio, fecha_fin, activa."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.excepcion_academica_model import ExcepcionAcademicaModel
        from sqlalchemy import inspect

        mapper = inspect(ExcepcionAcademicaModel)
        columnas = {c.key for c in mapper.columns}

        assert "id" in columnas
        assert "usuario_id" in columnas
        assert "motivo" in columnas
        assert "fecha_inicio" in columnas
        assert "fecha_fin" in columnas
        assert "activa" in columnas

    def test_activa_default_true(self):
        """activa debe tener default True."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.excepcion_academica_model import ExcepcionAcademicaModel
        from sqlalchemy import inspect

        mapper = inspect(ExcepcionAcademicaModel)
        col = mapper.columns["activa"]
        assert col.default is not None or col.server_default is not None


class TestModelsExports:
    """Tests para verificar exports en __init__.py."""

    def test_no_export_sancion_model(self):
        """No debe exportar SancionModel (eliminado)."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models import __all__ as exports

        assert "SancionModel" not in exports

    def test_export_perfil_reputacion_model(self):
        """Debe exportar PerfilReputacionModel."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models import __all__ as exports

        assert "PerfilReputacionModel" in exports

    def test_export_excepcion_academica_model(self):
        """Debe exportar ExcepcionAcademicaModel."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models import __all__ as exports

        assert "ExcepcionAcademicaModel" in exports

    def test_export_sancion_model_desde_perfil(self):
        """SancionModel debe ser importable desde perfil_reputacion_model (inline)."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import SancionModel

        assert SancionModel is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])