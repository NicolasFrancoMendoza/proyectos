import pymupdf

from config import (
    MIN_BLOCKS_FOR_COLUMNS,
    COLUMN_GAP_RATIO,
    MIN_COLUMN_SEPARATION_RATIO,
    FULL_WIDTH_RATIO,
    MIN_BLOCKS_PER_COLUMN,
    MIN_BLOCKS_PER_REGION,
    MIN_REGION_GAP_RATIO,
    MIN_REGION_HEIGHT_RATIO,
    REGION_BALANCE_RATIO,
)


def normalize(text):
    if not text:
        return ""

    text = text.replace("\r", "\n")

    lines = []

    for line in text.splitlines():

        line = " ".join(line.split())

        if line:
            lines.append(line)

    return "\n".join(lines).strip()


def open_pdf(path):
    return pymupdf.open(path)


def get_blocks(page):

    raw_blocks = page.get_text("blocks")

    blocks = []

    for idx, block in enumerate(raw_blocks):

        if len(block) < 5:
            continue

        x0, y0, x1, y1, text = block[:5]

        text = normalize(text)

        if not text:
            continue

        blocks.append({
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "cx": (x0 + x1) / 2,
            "cy": (y0 + y1) / 2,
            "width": x1 - x0,
            "height": y1 - y0,
            "text": text,
            "index": idx,
        })

    return blocks


def get_image_count(page):

    try:
        return len(page.get_images(full=True))
    except Exception:
        return 0


def detect_columns(blocks, page_width):

    if len(blocks) < MIN_BLOCKS_FOR_COLUMNS:
        return 1

    sorted_blocks = sorted(
        blocks,
        key=lambda b: b["cx"]
    )

    gaps = []

    for i in range(len(sorted_blocks) - 1):

        gap = (
            sorted_blocks[i + 1]["cx"]
            - sorted_blocks[i]["cx"]
        )

        gaps.append((gap, i))

    if not gaps:
        return 1

    max_gap, split_index = max(
        gaps,
        key=lambda item: item[0]
    )

    if max_gap < page_width * COLUMN_GAP_RATIO:
        return 1

    left = sorted_blocks[:split_index + 1]

    right = sorted_blocks[split_index + 1:]

    if (
        len(left) < MIN_BLOCKS_PER_COLUMN
        or len(right) < MIN_BLOCKS_PER_COLUMN
    ):
        return 1

    left_max = max(
        block["cx"]
        for block in left
    )

    right_min = min(
        block["cx"]
        for block in right
    )

    if (
        right_min - left_max
        < page_width * MIN_COLUMN_SEPARATION_RATIO
    ):
        return 1

    return 2


def detect_split_regions(
    blocks,
    page_height,
):
    """
    Detecta si una página física parece contener
    dos páginas lógicas apiladas verticalmente.

    Retorna:

        None

    o:

        {
            "split": True,
            "split_y": valor,
            "top_blocks": [...],
            "bottom_blocks": [...],
        }
    """

    if len(blocks) < MIN_BLOCKS_PER_REGION * 2:
        return None

    if page_height <= 0:
        return None

    sorted_blocks = sorted(
        blocks,
        key=lambda b: (
            b["y0"],
            b["x0"],
        )
    )

    # -----------------------------------------------------
    # Buscar el mayor vacío vertical entre bloques
    # -----------------------------------------------------

    gaps = []

    for i in range(len(sorted_blocks) - 1):

        current = sorted_blocks[i]

        following = sorted_blocks[i + 1]

        gap = (
            following["y0"]
            - current["y1"]
        )

        if gap > 0:

            gaps.append(
                (
                    gap,
                    current["y1"],
                    following["y0"],
                    i,
                )
            )

    if not gaps:
        return None

    max_gap, gap_start, gap_end, split_index = max(
        gaps,
        key=lambda item: item[0]
    )

    # -----------------------------------------------------
    # El espacio debe ser suficientemente grande
    # -----------------------------------------------------

    min_gap = (
        page_height
        * MIN_REGION_GAP_RATIO
    )

    if max_gap < min_gap:
        return None

    # -----------------------------------------------------
    # Punto de división
    # -----------------------------------------------------

    split_y = (
        gap_start + gap_end
    ) / 2

    top_blocks = [
        block
        for block in blocks
        if block["cy"] < split_y
    ]

    bottom_blocks = [
        block
        for block in blocks
        if block["cy"] >= split_y
    ]

    # -----------------------------------------------------
    # Ambas regiones deben tener suficiente contenido
    # -----------------------------------------------------

    if (
        len(top_blocks)
        < MIN_BLOCKS_PER_REGION
        or len(bottom_blocks)
        < MIN_BLOCKS_PER_REGION
    ):
        return None

    # -----------------------------------------------------
    # Evitar falso positivo:
    # una región no puede ser diminuta frente a la otra
    # -----------------------------------------------------

    total_blocks = (
        len(top_blocks)
        + len(bottom_blocks)
    )

    top_ratio = (
        len(top_blocks)
        / total_blocks
    )

    bottom_ratio = (
        len(bottom_blocks)
        / total_blocks
    )

    if (
        top_ratio < REGION_BALANCE_RATIO
        or bottom_ratio < REGION_BALANCE_RATIO
    ):
        return None

    # -----------------------------------------------------
    # Ambas regiones deben ocupar una parte razonable
    # de la página
    # -----------------------------------------------------

    top_y0 = min(
        block["y0"]
        for block in top_blocks
    )

    top_y1 = max(
        block["y1"]
        for block in top_blocks
    )

    bottom_y0 = min(
        block["y0"]
        for block in bottom_blocks
    )

    bottom_y1 = max(
        block["y1"]
        for block in bottom_blocks
    )

    top_height_ratio = (
        top_y1 - top_y0
    ) / page_height

    bottom_height_ratio = (
        bottom_y1 - bottom_y0
    ) / page_height

    if (
        top_height_ratio < MIN_REGION_HEIGHT_RATIO
        or bottom_height_ratio < MIN_REGION_HEIGHT_RATIO
    ):
        return None

    return {
        "split": True,
        "split_y": split_y,
        "top_blocks": top_blocks,
        "bottom_blocks": bottom_blocks,
    }