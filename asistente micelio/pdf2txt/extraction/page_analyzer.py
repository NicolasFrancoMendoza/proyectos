"""
extraction/page_analyzer.py
----------------------------
Misma lógica geométrica del analizador original (detección de columnas,
cambios de columna, retrocesos verticales, regiones divididas). El único
cambio respecto al código fuente es la salida: en vez de un `dict` suelto
(que permitía `analysis.get("extractor", "")` fallando en silencio ante
un typo), ahora se devuelve un `PageAnalysis` tipado, consumido por
`extraction/strategies.py`.
"""

from __future__ import annotations

from config import (
    FULL_WIDTH_RATIO,
    MIN_VERTICAL_TOLERANCE,
    MEDIAN_HEIGHT_MULTIPLIER,
    HIGH_SWITCHES,
    HIGH_BACKTRACKS,
)
from domain import ExtractorType, PageAnalysis
from extraction.pdf_reader import (
    normalize,
    detect_columns,
    detect_split_regions,
    get_image_count,
)


def detect_content_features(text: str) -> dict:
    lower = text.lower()

    table_words = ["cuadro ", "tabla ", "table ", "columnas", "filas"]
    figure_words = ["gráfico ", "grafico ", "figura ", "figure ", "mapa ", "diagrama "]
    list_indicators = ["•", " - ", "1.", "2.", "3.", "a.", "b.", "c."]

    return {
        "tiene_tabla": any(item in lower for item in table_words),
        "tiene_figura": any(item in lower for item in figure_words),
        "tiene_lista": any(item in text for item in list_indicators),
    }


def count_column_switches(blocks, columns, page_width) -> int:
    if columns != 2:
        return 0

    sequence = []
    for block in blocks:
        if block["width"] >= page_width * FULL_WIDTH_RATIO:
            continue
        sequence.append("L" if block["cx"] < page_width / 2 else "R")

    return sum(1 for i in range(1, len(sequence)) if sequence[i] != sequence[i - 1])


def count_backtracks(blocks, columns, page_width) -> int:
    if not blocks:
        return 0

    heights = sorted(max(1, b["height"]) for b in blocks)
    median_height = heights[len(heights) // 2]
    tolerance = max(MIN_VERTICAL_TOLERANCE, median_height * MEDIAN_HEIGHT_MULTIPLIER)

    if columns == 1:
        ordered = sorted(blocks, key=lambda b: (b["y0"], b["x0"]))
        previous_y, backtracks = None, 0
        for block in ordered:
            if previous_y is not None and block["y0"] < previous_y - tolerance:
                backtracks += 1
            previous_y = block["y0"]
        return backtracks

    midpoint = page_width / 2
    backtracks = 0
    for side in ["L", "R"]:
        column_blocks = [
            b for b in blocks
            if (b["cx"] < midpoint if side == "L" else b["cx"] >= midpoint)
        ]
        column_blocks.sort(key=lambda b: (b["y0"], b["x0"]))
        previous_y = None
        for block in column_blocks:
            if previous_y is not None and block["y0"] < previous_y - tolerance:
                backtracks += 1
            previous_y = block["y0"]
    return backtracks


def choose_extractor(
    columns: int,
    features: dict,
    split_regions: dict | None,
) -> ExtractorType:
    # 1. Página física dividida en dos regiones lógicas.
    if split_regions:
        return ExtractorType.TEXT_REGION

    # 2. Dos columnas: se respeta el orden nativo del PDF (comportamiento
    #    validado previamente); no se usa LLM ni SORT aquí.
    if columns == 2:
        return ExtractorType.TEXT

    # 3. LLM solo para páginas realmente complejas (tabla o figura).
    if features["tiene_tabla"] or features["tiene_figura"]:
        return ExtractorType.LLM

    # 4. Página normal.
    return ExtractorType.TEXT


def analyze_page(page, blocks) -> PageAnalysis:
    page_width = page.rect.width
    page_height = page.rect.height

    text = normalize(page.get_text("text"))
    columns = detect_columns(blocks, page_width)
    switches = count_column_switches(blocks, columns, page_width)
    backtracks = count_backtracks(blocks, columns, page_width)
    split_regions = detect_split_regions(blocks, page_height)
    features = detect_content_features(text)
    extractor = choose_extractor(columns, features, split_regions)

    complexity = "BAJA"
    if columns == 2 or split_regions:
        complexity = "MEDIA"
    if features["tiene_tabla"] or features["tiene_figura"]:
        complexity = "ALTA"
    if switches >= HIGH_SWITCHES or backtracks >= HIGH_BACKTRACKS:
        complexity = "ALTA"

    return PageAnalysis(
        extractor=extractor,
        complejidad=complexity,
        columnas=columns,
        bloques=len(blocks),
        imagenes=get_image_count(page),
        cambios_columna=switches,
        retrocesos_y=backtracks,
        tiene_tabla=features["tiene_tabla"],
        tiene_figura=features["tiene_figura"],
        tiene_lista=features["tiene_lista"],
        tiene_region_dividida=bool(split_regions),
        split_y=split_regions["split_y"] if split_regions else None,
    )
