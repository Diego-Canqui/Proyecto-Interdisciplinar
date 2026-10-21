from uuid import uuid4
import pytest
from prestamos_recursos.contexts.catalogo.domain.entities.recurso import Recurso
from prestamos_recursos.contexts.catalogo.domain.enums import EstadoRecurso
from prestamos_recursos.contexts.catalogo.domain.value_objects.ficha_tecnica import FichaTecnica


def test_ficha_tecnica_valida():
    ficha = FichaTecnica(
        marca="Dell",
        modelo="Latitude",
        numero_serie="SN123456",
        color="Negro",
        estado_fisico="Excelente",
        foto_url="http://example.com/foto.jpg"
    )
    assert ficha.es_valida() is True


def test_recurso_marcar_disponible():
    ficha = FichaTecnica(
        marca="Dell",
        modelo="Latitude",
        numero_serie="SN123456",
        color="Negro",
        estado_fisico="Excelente",
        foto_url="http://example.com/foto.jpg"
    )
    recurso = Recurso(
        id=uuid4(),
        nombre="Laptop Dell",
        descripcion="Laptop de prueba",
        categoria="Computadoras",
        estado=EstadoRecurso.EN_USO,
        ficha_tecnica=ficha
    )
    recurso.marcar_disponible()
    assert recurso.estado == EstadoRecurso.DISPONIBLE


def test_recurso_no_disponible_si_fuera_de_servicio():
    ficha = FichaTecnica(
        marca="Dell",
        modelo="Latitude",
        numero_serie="SN123456",
        color="Negro",
        estado_fisico="Dañado",
        foto_url="http://example.com/foto.jpg"
    )
    recurso = Recurso(
        id=uuid4(),
        nombre="Laptop Dell",
        descripcion="Laptop rota",
        categoria="Computadoras",
        estado=EstadoRecurso.FUERA_DE_SERVICIO,
        ficha_tecnica=ficha
    )
    with pytest.raises(ValueError):
        recurso.marcar_disponible()
