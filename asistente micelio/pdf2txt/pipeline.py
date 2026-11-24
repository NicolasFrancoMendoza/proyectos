"""
pipeline.py
-----------
Orquestador central. Encadena las cuatro etapas:

    1. classification.inspector   -> DocumentProfile (¿se puede procesar?)
    2. extraction (analyzer+strategies) -> texto por página
    3. ocr.registry (opcional)    -> solo si la calidad falla Y está activo
    4. validation.quality_gate    -> QualityReport por página

Principio de diseño: cada página se procesa de forma aislada. Un error
en una página (extractor que lanza excepción, imagen corrupta) se
registra y NO interrumpe ni el resto del documento ni el resto del lote
— a diferencia del original, donde el único `try/except` envolvía el
documento completo en `main.py`.
"""

from __future__ import annotations

import logging

import pymupdf

from classification.inspector import inspect_pdf
from domain import (
    DocumentIssue,
    DocumentResult,
    ExtractorType,
    PageResult,
    QualityStatus,
)
from extraction.page_analyzer import analyze_page
from extraction.pdf_reader import get_blocks
from extraction.strategies import extract_with_strategy
from ocr.registry import get_active_provider
from validation.quality_gate import evaluate_text

logger = logging.getLogger("pdf2text.pipeline")


def _run_ocr_fallback(page: "pymupdf.Page", page_number: int) -> str | None:
    """Intenta OCR sobre el render de la página, si hay un proveedor activo.
    Devuelve None si OCR está desactivado o si falla, nunca lanza excepción."""
    provider = get_active_provider()
    if provider is None:
        return None

    try:
        pix = page.get_pixmap(dpi=200)
        image_bytes = pix.tobytes("png")
        result = provider.extract_text_from_image(image_bytes)
        logger.info(
            "OCR (%s) aplicado a página %s: %d caracteres.",
            result.provider_name, page_number, len(result.text),
        )
        return result.text
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo en OCR para página %s: %s", page_number, exc)
        return None


def process_page(doc: "pymupdf.Document", page: "pymupdf.Page", page_index: int) -> PageResult:
    page_number = page_index + 1

    try:
        blocks = get_blocks(page)
        analysis = analyze_page(page, blocks)
        text, extractor_used = extract_with_strategy(doc, page, page_index, analysis)
    except Exception as exc:  # noqa: BLE001 - aislamos cualquier fallo a nivel de página
        logger.error("Fallo irrecuperable en página %s: %s", page_number, exc)
        return PageResult(
            page_number=page_number,
            text="",
            extractor_used=ExtractorType.TEXT_FALLBACK,
            error=str(exc),
            quality=evaluate_text(""),
        )

    quality = evaluate_text(text)
    ocr_used = False

    if not quality.passed:
        logger.warning(
            "Página %s no pasó el control de calidad (%s). Intentando OCR si está disponible.",
            page_number, quality.status.value,
        )
        ocr_text = _run_ocr_fallback(page, page_number)
        if ocr_text:
            ocr_quality = evaluate_text(ocr_text)
            if ocr_quality.passed or ocr_quality.char_count > quality.char_count:
                text, quality, ocr_used = ocr_text, ocr_quality, True
                extractor_used = ExtractorType.OCR

    return PageResult(
        page_number=page_number,
        text=text,
        extractor_used=extractor_used,
        analysis=analysis,
        quality=quality,
        ocr_used=ocr_used,
    )


def process_document(path) -> DocumentResult:
    filename = path.name
    logger.info("Procesando: %s", filename)

    profile = inspect_pdf(path)

    if not profile.is_processable:
        logger.warning(
            "Documento omitido (%s): %s", profile.issue.value, filename
        )
        return DocumentResult(
            filename=filename,
            profile=profile,
            skipped=True,
            skip_reason=profile.error_message or profile.issue.value,
        )

    result = DocumentResult(filename=filename, profile=profile)

    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # noqa: BLE001
        result.skipped = True
        result.skip_reason = f"No se pudo reabrir el documento para extracción: {exc}"
        return result

    try:
        for page_index, page in enumerate(doc):
            page_result = process_page(doc, page, page_index)
            result.pages.append(page_result)
            logger.info(
                "  Página %s: %s / calidad=%s",
                page_result.page_number,
                page_result.extractor_used.value,
                page_result.quality.status.value if page_result.quality else "N/A",
            )
    finally:
        doc.close()

    return result
