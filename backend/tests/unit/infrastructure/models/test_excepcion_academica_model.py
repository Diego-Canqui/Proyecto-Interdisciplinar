"""Tests para el modelo de BD ExcepcionAcademicaModel."""
import pytest
from datetime import datetime
from uuid import UUID, uuid4


@pytest.mark.unit
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

    def test_tipos_columnas(self):
        """Verificar tipos de columnas correctos."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.excepcion_academica_model import ExcepcionAcademicaModel
        from sqlalchemy import inspect, UUID as SAUUID, Text, DateTime, Boolean

        mapper = inspect(ExcepcionAcademicaModel)
        cols = {c.key: c for c in mapper.columns}

        # id: UUID PK
        assert isinstance(cols["id"].type, SAUUID)
        assert cols["id"].primary_key

        # usuario_id: UUID
        assert isinstance(cols["usuario_id"].type, SAUUID)

        # motivo: Text
        assert isinstance(cols["motivo"].type, Text)

        # fecha_inicio, fecha_fin: DateTime(timezone=True)
        assert isinstance(cols["fecha_inicio"].type, DateTime)
        assert cols["fecha_inicio"].type.timezone is True
        assert isinstance(cols["fecha_fin"].type, DateTime)
        assert cols["fecha_fin"].type.timezone is True

        # activa: Boolean
        assert isinstance(cols["activa"].type, Boolean)

    def test_activa_default_true(self):
        """activa debe tener default True."""
        from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.excepcion_academica_model import ExcepcionAcademicaModel
        from sqlalchemy import inspect

        mapper = inspect(ExcepcionAcademicaModel)
        col = mapper.columns["activa"]
        assert col.default is not None or col.server_default is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])