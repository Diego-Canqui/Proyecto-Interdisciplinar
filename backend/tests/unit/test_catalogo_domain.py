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


def test_ficha_tecnica_campos_opcionales_y_especificaciones_por_defecto():
    ficha = FichaTecnica(
        estado_fisico="Bueno",
        foto_url="http://example.com/libro.jpg",
    )
    assert ficha.marca is None
    assert ficha.modelo is None
    assert ficha.numero_serie is None
    assert ficha.color is None
    assert ficha.especificaciones == {}
    assert ficha.es_valida() is True


def test_ficha_tecnica_normaliza_cadenas_vacias_a_none():
    ficha = FichaTecnica(
        marca="",
        modelo="   ",
        numero_serie="  \t ",
        color="",
        estado_fisico="Bueno",
        foto_url="http://example.com/libro.jpg",
        especificaciones={"autor": "Erich Gamma", "isbn": "978-0201633610"},
    )
    assert ficha.marca is None
    assert ficha.modelo is None
    assert ficha.numero_serie is None
    assert ficha.color is None
    assert ficha.especificaciones == {"autor": "Erich Gamma", "isbn": "978-0201633610"}
    assert ficha.es_valida() is True


def test_ficha_tecnica_invalida_sin_estado_fisico_o_especificaciones_no_dict():
    ficha_sin_estado = FichaTecnica(
        estado_fisico="   ",
        foto_url="http://example.com/libro.jpg",
    )
    assert ficha_sin_estado.es_valida() is False

    ficha_espec_invalida = FichaTecnica(
        estado_fisico="Bueno",
        foto_url="http://example.com/libro.jpg",
        especificaciones="no-es-dict",  # type: ignore[arg-type]
    )
    assert ficha_espec_invalida.es_valida() is False
