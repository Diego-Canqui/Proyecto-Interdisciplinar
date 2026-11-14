import pytest

from prestamos_recursos.contexts.prestamos.domain.services.plantilla_checklist import (
    obtener_items_checklist_por_categoria,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "categoria",
    ["Electrónica", "Laptops", "Cómputo", "laptops", "COMPUTO"],
)
def test_plantilla_checklist_electronica(categoria: str):
    items = obtener_items_checklist_por_categoria(categoria)
    assert len(items) >= 3
    ids = {item["id"] for item in items}
    assert "carcasa" in ids or "pantalla" in ids
    for item in items:
        assert set(item.keys()) == {"id", "etiqueta", "descripcion_ok", "descripcion_fallo"}
        assert all(isinstance(v, str) and v.strip() for v in item.values())


@pytest.mark.unit
@pytest.mark.parametrize("categoria", ["Libros", "Bibliografía", "libros"])
def test_plantilla_checklist_libros(categoria: str):
    items = obtener_items_checklist_por_categoria(categoria)
    assert len(items) >= 3
    etiquetas = " ".join(item["etiqueta"].lower() for item in items)
    assert "páginas" in etiquetas or "portada" in etiquetas or "lomo" in etiquetas
    for item in items:
        assert set(item.keys()) == {"id", "etiqueta", "descripcion_ok", "descripcion_fallo"}


@pytest.mark.unit
@pytest.mark.parametrize("categoria", ["Audio y Video", "Fotografía", "Audio", "Video"])
def test_plantilla_checklist_audio_video(categoria: str):
    items = obtener_items_checklist_por_categoria(categoria)
    assert len(items) >= 3
    for item in items:
        assert set(item.keys()) == {"id", "etiqueta", "descripcion_ok", "descripcion_fallo"}


@pytest.mark.unit
def test_plantilla_checklist_laboratorio():
    items = obtener_items_checklist_por_categoria("Laboratorio")
    assert len(items) >= 3
    for item in items:
        assert set(item.keys()) == {"id", "etiqueta", "descripcion_ok", "descripcion_fallo"}


@pytest.mark.unit
@pytest.mark.parametrize("categoria", ["", "Mobiliario", "Otra categoría"])
def test_plantilla_checklist_generica(categoria: str):
    items = obtener_items_checklist_por_categoria(categoria)
    assert len(items) >= 2
    ids = {item["id"] for item in items}
    assert "estado_general" in ids
    for item in items:
        assert set(item.keys()) == {"id", "etiqueta", "descripcion_ok", "descripcion_fallo"}
