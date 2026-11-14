from __future__ import annotations

import unicodedata


def _normalizar_categoria(categoria: str) -> str:
    """Normaliza la categoría a minúsculas y sin tildes para emparejar plantillas."""
    texto = unicodedata.normalize("NFD", categoria.strip().lower())
    return "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")


_PLANTILLA_ELECTRONICA: list[dict[str, str]] = [
    {
        "id": "carcasa",
        "etiqueta": "Carcasa y estructura sin golpes ni fisuras",
        "descripcion_ok": "Carcasa íntegra",
        "descripcion_fallo": "Carcasa dañada o con fisuras",
    },
    {
        "id": "pantalla",
        "etiqueta": "Pantalla o panel sin rayaduras ni píxeles muertos",
        "descripcion_ok": "Pantalla en buen estado",
        "descripcion_fallo": "Pantalla con daños o fallos",
    },
    {
        "id": "cables",
        "etiqueta": "Cargador, cables y accesorios completos",
        "descripcion_ok": "Cables y accesorios completos",
        "descripcion_fallo": "Faltan cables o presentan desgaste",
    },
    {
        "id": "serie",
        "etiqueta": "Número de serie y encendido verificado",
        "descripcion_ok": "Encendido y serie verificados",
        "descripcion_fallo": "No enciende o serie ilegible",
    },
]

_PLANTILLA_AUDIO_VIDEO: list[dict[str, str]] = [
    {
        "id": "lente_cuerpo",
        "etiqueta": "Lente, cuerpo o cápsula sin rayaduras ni golpes",
        "descripcion_ok": "Lente y cuerpo limpios e íntegros",
        "descripcion_fallo": "Lente o cuerpo con rayaduras o golpes",
    },
    {
        "id": "bateria_carga",
        "etiqueta": "Batería, cargador y tarjetas de memoria incluidos",
        "descripcion_ok": "Batería y accesorios completos",
        "descripcion_fallo": "Falta batería, cargador o accesorio",
    },
    {
        "id": "prueba_funcionamiento",
        "etiqueta": "Prueba rápida de encendido, audio o captura",
        "descripcion_ok": "Funcionamiento verificado",
        "descripcion_fallo": "Presenta fallo de audio o captura",
    },
]

_PLANTILLA_LIBROS: list[dict[str, str]] = [
    {
        "id": "portada_lomo",
        "etiqueta": "Portada, contraportada y lomo íntegros",
        "descripcion_ok": "Portada y lomo en buen estado",
        "descripcion_fallo": "Portada o lomo deteriorado",
    },
    {
        "id": "paginas",
        "etiqueta": "Páginas completas sin roturas, humedad ni subrayados",
        "descripcion_ok": "Páginas completas y limpias",
        "descripcion_fallo": "Páginas faltantes, manchadas o rayadas",
    },
    {
        "id": "codigo_ejemplar",
        "etiqueta": "Código de ejemplar o ISBN legible",
        "descripcion_ok": "Código de ejemplar verificado",
        "descripcion_fallo": "Etiqueta o código dañado",
    },
]

_PLANTILLA_LABORATORIO: list[dict[str, str]] = [
    {
        "id": "integridad_material",
        "etiqueta": "Material sin fisuras, oxidación ni piezas sueltas",
        "descripcion_ok": "Material en condiciones óptimas",
        "descripcion_fallo": "Material con fisuras o desgaste",
    },
    {
        "id": "calibracion_limpieza",
        "etiqueta": "Limpieza y calibración básica verificada",
        "descripcion_ok": "Limpio y calibrado",
        "descripcion_fallo": "Requiere limpieza o recalibración",
    },
    {
        "id": "accesorios_seguridad",
        "etiqueta": "Estuche, puntas o accesorios de seguridad completos",
        "descripcion_ok": "Accesorios completos",
        "descripcion_fallo": "Faltan accesorios o estuche",
    },
]

_PLANTILLA_GENERICA: list[dict[str, str]] = [
    {
        "id": "estado_general",
        "etiqueta": "Estado físico general sin daños visibles",
        "descripcion_ok": "Estado físico conforme",
        "descripcion_fallo": "Presenta daños físicos visibles",
    },
    {
        "id": "componentes",
        "etiqueta": "Piezas, estuche o complementos completos",
        "descripcion_ok": "Componentes completos",
        "descripcion_fallo": "Faltan piezas o complementos",
    },
    {
        "id": "identificacion",
        "etiqueta": "Etiqueta o código de inventario legible",
        "descripcion_ok": "Identificación verificada",
        "descripcion_fallo": "Identificación ausente o ilegible",
    },
]


def obtener_items_checklist_por_categoria(categoria: str) -> list[dict[str, str]]:
    """Retorna la plantilla de ítems de inspección física según la categoría del recurso."""
    norm = _normalizar_categoria(categoria or "")
    if any(clave in norm for clave in ("electronica", "laptop", "computo")):
        return [dict(item) for item in _PLANTILLA_ELECTRONICA]
    if any(clave in norm for clave in ("audio", "video", "fotografia")):
        return [dict(item) for item in _PLANTILLA_AUDIO_VIDEO]
    if any(clave in norm for clave in ("libro", "bibliografia")):
        return [dict(item) for item in _PLANTILLA_LIBROS]
    if "laboratorio" in norm:
        return [dict(item) for item in _PLANTILLA_LABORATORIO]
    return [dict(item) for item in _PLANTILLA_GENERICA]
