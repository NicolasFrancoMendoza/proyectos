"""
classification/inspector.py
----------------------------
Etapa 1 del pipeline: inspecciona un PDF ANTES de intentar extraer texto,
para detectar de antemano los casos que el resto del pipeline no sabe
manejar bien: archivos cifrados, corruptos/mal formados, o compuestos
íntegramente por imágenes (escaneos sin capa de texto).

Esto evita el patrón actual, donde un PDF problemático simplemente
produce texto vacío o lanza una excepción a mitad de `main.py` y
puede interrumpir el procesamiento de los demás archivos del lote.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pymupdf

from domain import DocumentIssue, DocumentProfile, PageClassification

logger = logging.getLogger("pdf2text.inspector")

# Si una página tiene menos de este número de caracteres de texto nativo
# Y al menos una imagen que cubre una fracción relevante de la página,
# se considera "solo imagen" (candidata a OCR).
MIN_TEXT_CHARS_FOR_NATIVE_PAGE = 20
MIN_IMAGE_COVERAGE_FOR_SCAN = 0.60


def _page_image_coverage(page: "pymupdf.Page") -> float:
    """Estima qué fracción del área de la página está cubierta por imágenes."""
    try:
        images = page.get_images(full=True)
    except Exception:
        return 0.0

    if not images:
        return 0.0

    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return 0.0

    covered = 0.0
    for img in images:
        xref = img[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            continue
        for rect in rects:
            covered += rect.width * rect.height

    return min(covered / page_area, 1.0)


def classify_page(page: "pymupdf.Page", page_number: int) -> PageClassification:
    try:
        text = page.get_text("text") or ""
    except Exception as exc:  # noqa: BLE001 - queremos capturar cualquier fallo del parser
        logger.warning("No se pudo leer texto de la página %s: %s", page_number, exc)
        text = ""

    char_count = len(text.strip())
    coverage = _page_image_coverage(page)

    is_image_only = (
        char_count < MIN_TEXT_CHARS_FOR_NATIVE_PAGE
        and coverage >= MIN_IMAGE_COVERAGE_FOR_SCAN
    )

    return PageClassification(
        page_number=page_number,
        is_image_only=is_image_only,
        image_coverage_ratio=coverage,
        char_count=char_count,
    )


def inspect_pdf(path: Path) -> DocumentProfile:
    """
    Punto de entrada de la etapa de clasificación.

    Nunca lanza excepciones hacia afuera: cualquier problema se traduce
    en un DocumentProfile con el `issue` correspondiente, para que el
    pipeline decida (registrar y saltar, o continuar) sin romper el lote.
    """
    profile = DocumentProfile(path=path)

    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # noqa: BLE001
        profile.issue = DocumentIssue.CORRUPTED
        profile.error_message = str(exc)
        logger.error("PDF corrupto o ilegible: %s (%s)", path.name, exc)
        return profile

    try:
        if doc.is_encrypted:
            # intenta abrir con contraseña vacía (común en PDFs "protegidos"
            # solo contra edición, no contra lectura)
            if not doc.authenticate(""):
                profile.issue = DocumentIssue.ENCRYPTED
                profile.is_encrypted = True
                profile.error_message = "El documento requiere contraseña."
                logger.warning("PDF cifrado, no se pudo autenticar: %s", path.name)
                doc.close()
                return profile

        page_count = doc.page_count
        profile.page_count = page_count

        if page_count == 0:
            profile.issue = DocumentIssue.EMPTY
            doc.close()
            return profile

        pages: list[PageClassification] = []
        for index, page in enumerate(doc):
            pages.append(classify_page(page, index + 1))
        profile.pages = pages

        image_only_pages = sum(1 for p in pages if p.is_image_only)
        if page_count > 0 and image_only_pages / page_count >= 0.8:
            profile.issue = DocumentIssue.SCANNED_IMAGE_ONLY
            logger.info(
                "PDF detectado como escaneado (%s/%s páginas sin texto nativo): %s",
                image_only_pages,
                page_count,
                path.name,
            )
        else:
            profile.issue = DocumentIssue.NONE

    except Exception as exc:  # noqa: BLE001 - robustez ante parsers mal formados
        profile.issue = DocumentIssue.CORRUPTED
        profile.error_message = str(exc)
        logger.error("Error inesperado inspeccionando %s: %s", path.name, exc)
    finally:
        doc.close()

    return profile
