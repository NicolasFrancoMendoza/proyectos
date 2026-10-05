from config import (
    FULL_WIDTH_RATIO,
    MIN_VERTICAL_TOLERANCE,
    MEDIAN_HEIGHT_MULTIPLIER,
    HIGH_SWITCHES,
    HIGH_BACKTRACKS,
    SORT_SWITCHES,
    SORT_BACKTRACKS,
)

from pdf_reader import (
    normalize,
    detect_columns,
    detect_split_regions,
    get_image_count,
)


def detect_content_features(page, text):

    lower = text.lower()

    table_words = [
        "cuadro ",
        "tabla ",
        "table ",
        "columnas",
        "filas",
    ]

    figure_words = [
        "gráfico ",
        "grafico ",
        "figura ",
        "figure ",
        "mapa ",
        "diagrama ",
    ]

    list_indicators = [
        "•",
        " - ",
        "1.",
        "2.",
        "3.",
        "a.",
        "b.",
        "c.",
    ]

    return {
        "tiene_tabla": any(
            item in lower
            for item in table_words
        ),

        "tiene_figura": any(
            item in lower
            for item in figure_words
        ),

        "tiene_lista": any(
            item in text
            for item in list_indicators
        ),
    }


def count_column_switches(
    blocks,
    columns,
    page_width,
):

    if columns != 2:
        return 0

    sequence = []

    for block in blocks:

        if (
            block["width"]
            >= page_width * FULL_WIDTH_RATIO
        ):
            continue

        if block["cx"] < page_width / 2:
            sequence.append("L")
        else:
            sequence.append("R")

    switches = 0

    for i in range(1, len(sequence)):

        if sequence[i] != sequence[i - 1]:
            switches += 1

    return switches


def count_backtracks(
    blocks,
    columns,
    page_width,
):

    if not blocks:
        return 0

    heights = sorted(
        max(1, block["height"])
        for block in blocks
    )

    median_height = heights[
        len(heights) // 2
    ]

    tolerance = max(
        MIN_VERTICAL_TOLERANCE,
        median_height * MEDIAN_HEIGHT_MULTIPLIER,
    )

    if columns == 1:

        ordered = sorted(
            blocks,
            key=lambda b: (
                b["y0"],
                b["x0"],
            ),
        )

        previous_y = None
        backtracks = 0

        for block in ordered:

            if (
                previous_y is not None
                and block["y0"]
                < previous_y - tolerance
            ):
                backtracks += 1

            previous_y = block["y0"]

        return backtracks

    midpoint = page_width / 2

    backtracks = 0

    for side in ["L", "R"]:

        column_blocks = [
            block
            for block in blocks
            if (
                block["cx"] < midpoint
                if side == "L"
                else block["cx"] >= midpoint
            )
        ]

        column_blocks.sort(
            key=lambda b: (
                b["y0"],
                b["x0"],
            )
        )

        previous_y = None

        for block in column_blocks:

            if (
                previous_y is not None
                and block["y0"]
                < previous_y - tolerance
            ):
                backtracks += 1

            previous_y = block["y0"]

    return backtracks


def choose_extractor(
    columns,
    switches,
    backtracks,
    features,
    split_regions,
):

    # --------------------------------------------------
    # 1. Una página física dividida verticalmente
    #    en dos regiones lógicas.
    #
    #    Esto sí necesita extracción por regiones.
    # --------------------------------------------------

    if split_regions:
        return "TEXT_REGION"

    # --------------------------------------------------
    # 2. DOS COLUMNAS
    #
    #    IMPORTANTE:
    #    usamos TEXT, igual que V2.
    #
    #    NO usamos LLM aquí.
    #    NO usamos SORT aquí.
    #
    #    El orden nativo del PDF fue el comportamiento
    #    correcto observado en V2.
    # --------------------------------------------------

    if columns == 2:
        return "TEXT"

    # --------------------------------------------------
    # 3. LLM solamente para páginas realmente complejas.
    #
    #    Tabla/figura/lista por sí solas NO justifican
    #    LLM.
    # --------------------------------------------------

    if features["tiene_tabla"]:
        return "LLM"

    if features["tiene_figura"]:
        return "LLM"

    # --------------------------------------------------
    # 4. Página normal
    # --------------------------------------------------

    return "TEXT"


def analyze_page(page, blocks):

    page_width = page.rect.width
    page_height = page.rect.height

    text = normalize(
        page.get_text("text")
    )

    columns = detect_columns(
        blocks,
        page_width,
    )

    switches = count_column_switches(
        blocks,
        columns,
        page_width,
    )

    backtracks = count_backtracks(
        blocks,
        columns,
        page_width,
    )

    split_regions = detect_split_regions(
        blocks,
        page_height,
    )

    features = detect_content_features(
        page,
        text,
    )

    extractor = choose_extractor(
        columns,
        switches,
        backtracks,
        features,
        split_regions,
    )

    # --------------------------------------------------
    # COMPLEJIDAD
    # --------------------------------------------------

    complexity = "BAJA"

    if (
        columns == 2
        or split_regions
    ):
        complexity = "MEDIA"

    if (
        features["tiene_tabla"]
        or features["tiene_figura"]
    ):
        complexity = "ALTA"

    if (
        switches >= HIGH_SWITCHES
        or backtracks >= HIGH_BACKTRACKS
    ):
        complexity = "ALTA"

    return {
        "extractor": extractor,

        "complejidad": complexity,

        "columnas": columns,

        "bloques": len(blocks),

        "imagenes": get_image_count(page),

        "cambios_columna": switches,

        "retrocesos_y": backtracks,

        "tiene_tabla": features["tiene_tabla"],

        "tiene_figura": features["tiene_figura"],

        "tiene_lista": features["tiene_lista"],

        "tiene_region_dividida": bool(
            split_regions
        ),

        "split_y": (
            split_regions["split_y"]
            if split_regions
            else None
        ),
    }