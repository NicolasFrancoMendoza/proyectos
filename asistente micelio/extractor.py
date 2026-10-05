import pymupdf4llm


def extract_text(page):

    text = page.get_text(
        "text"
    )

    return text.strip()


def extract_sorted(page):

    text = page.get_text(
        "text",
        sort=True,
    )

    return text.strip()


def extract_text_region(
    page,
    split_y,
):

    page_rect = page.rect

    top_rect = (
        page_rect.x0,
        page_rect.y0,
        page_rect.x1,
        split_y,
    )

    bottom_rect = (
        page_rect.x0,
        split_y,
        page_rect.x1,
        page_rect.y1,
    )

    top_text = page.get_text(
        "text",
        clip=top_rect,
        sort=True,
    ).strip()

    bottom_text = page.get_text(
        "text",
        clip=bottom_rect,
        sort=True,
    ).strip()

    parts = []

    if top_text:
        parts.append(
            top_text
        )

    if bottom_text:
        parts.append(
            bottom_text
        )

    return "\n\n".join(
        parts
    ).strip()


def extract_llm(
    doc,
    page_number,
):

    markdown = pymupdf4llm.to_markdown(
        doc,
        pages=[page_number],
        write_images=False,
        show_progress=False,
    )

    return markdown.strip()


def extract_page(
    doc,
    page,
    page_index,
    extractor,
    analysis=None,
):

    if extractor == "TEXT":

        text = extract_text(
            page
        )

    elif extractor == "SORT":

        text = extract_sorted(
            page
        )

    elif extractor == "TEXT_REGION":

        if (
            analysis is None
            or analysis.get("split_y") is None
        ):
            text = extract_text(
                page
            )

        else:
            text = extract_text_region(
                page,
                analysis["split_y"],
            )

    elif extractor == "LLM":

        text = extract_llm(
            doc,
            page_index,
        )

    else:

        raise ValueError(
            f"Extractor desconocido: {extractor}"
        )

    # --------------------------------------------------
    # FALLBACK
    # --------------------------------------------------

    if not text.strip():

        text = extract_text(
            page
        )

        extractor_used = (
            "TEXT_FALLBACK"
        )

    else:

        extractor_used = extractor

    return {
        "text": text,
        "extractor": extractor_used,
    }