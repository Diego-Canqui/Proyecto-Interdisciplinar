from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.prestamos.domain.entities.checklist import Checklist
from prestamos_recursos.contexts.prestamos.domain.entities.garantia import Garantia
from prestamos_recursos.contexts.prestamos.domain.enums.estado_garantia import EstadoGarantia
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_checklist import TipoChecklist
from prestamos_recursos.contexts.prestamos.domain.enums.tipo_garantia import TipoGarantia
from prestamos_recursos.contexts.prestamos.domain.value_objects.compromiso_responsabilidad import (
    CompromisoResponsabilidad,
)
from prestamos_recursos.contexts.prestamos.infrastructure.models.checklist_model import (
    ChecklistModel,
)
from prestamos_recursos.contexts.prestamos.infrastructure.models.garantia_model import (
    GarantiaModel,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_checklist_repository import (
    SqlChecklistRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_garantia_repository import (
    SqlGarantiaRepository,
)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS prestamos")
        ChecklistModel.__table__.create(connection)
        GarantiaModel.__table__.create(connection)
    return Session(engine, expire_on_commit=False)


@pytest.mark.integration
def test_guardar_y_recuperar_checklist_con_fotos_urls():
    session = make_session()
    repo = SqlChecklistRepository(session)
    prestamo_id = uuid4()

    checklist = Checklist(
        prestamo_id=prestamo_id,
        tipo=TipoChecklist.ESTADO_INICIAL,
        fecha_inspeccion=datetime.now(UTC),
        observaciones="Carcasa intacta",
        fotos_urls=["https://storage.test/foto1.jpg", "https://storage.test/foto2.jpg"],
        completo=True,
    )

    # Debe hacer flush inmediato dentro de la sesión sin commit explícito previo
    repo.guardar(checklist)

    recuperado = repo.obtener_por_id(checklist.id)
    assert recuperado is not None
    assert recuperado.id == checklist.id
    assert recuperado.prestamo_id == prestamo_id
    assert recuperado.tipo == TipoChecklist.ESTADO_INICIAL
    assert recuperado.observaciones == "Carcasa intacta"
    assert recuperado.fotos_urls == [
        "https://storage.test/foto1.jpg",
        "https://storage.test/foto2.jpg",
    ]
    assert recuperado.completo is True

    # Comprobar actualización de fotos_urls
    checklist.fotos_urls.append("https://storage.test/foto3.jpg")
    repo.guardar(checklist)

    actualizado = repo.obtener_por_id(checklist.id)
    assert actualizado is not None
    assert len(actualizado.fotos_urls) == 3
    assert "https://storage.test/foto3.jpg" in actualizado.fotos_urls


@pytest.mark.integration
def test_guardar_y_recuperar_garantia_con_flush():
    session = make_session()
    repo = SqlGarantiaRepository(session)
    prestamo_id = uuid4()

    garantia = Garantia(
        prestamo_id=prestamo_id,
        tipo=TipoGarantia.CARNET_UNIVERSITARIO,
        estado=EstadoGarantia.REGISTRADA,
        fecha_registro=datetime.now(UTC),
        compromiso=CompromisoResponsabilidad(
            contenido="Acepto la custodia del bien",
            fecha_firma=datetime.now(UTC),
            firma_url="https://storage.test/firma.png",
            testigo="Guardalmacén",
        ),
    )

    repo.guardar(garantia)

    recuperada = repo.obtener_por_prestamo(prestamo_id)
    assert recuperada is not None
    assert recuperada.id == garantia.id
    assert recuperada.estado == EstadoGarantia.REGISTRADA
    assert recuperada.compromiso.testigo == "Guardalmacén"
