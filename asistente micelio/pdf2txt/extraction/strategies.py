"""
extraction/strategies.py
--------------------------
Cada forma de extraer texto (TEXT, SORT, TEXT_REGION, LLM) se expresa
como una clase que implementa `ExtractionStrategy`. Esto reemplaza el
`if/elif` monolítico de `extract_page()` en el código original: agregar
un extractor nuevo significa escribir una clase nueva y registrarla,
sin tocar las demás.
"""

from __future__ import annotations

import logging
from typing import Protocol

import pymupdf
import pymupdf4llm

from domain import ExtractorType, PageAnalysis

logger = logging.getLogger("pdf2text.extraction")


class ExtractionStrategy(Protocol):
    extractor_type: ExtractorType

    def extract(
        self,
        doc: "pymupdf.Document",
        page: "pymupdf.Page",
        page_index: int,
        analysis: PageAnalysis,
    ) -> str:
        ...


class TextStrategy:
    extractor_type = ExtractorType.TEXT

    def extract(self, doc, page, page_index, analysis) -> str:
        return page.get_text("text").strip()


class SortStrategy:
    extractor_type = ExtractorType.SORT

    def extract(self, doc, page, page_index, analysis) -> str:
        return page.get_text("text", sort=True).strip()


class TextRegionStrategy:
    extractor_type = ExtractorType.TEXT_REGION

    def extract(self, doc, page, page_index, analysis) -> str:
        if analysis.split_y is None:
            return page.get_text("text").strip()

        page_rect = page.rect
        top_rect = (page_rect.x0, page_rect.y0, page_rect.x1, analysis.split_y)
        bottom_rect = (page_rect.x0, analysis.split_y, page_rect.x1, page_rect.y1)

        top_text = page.get_text("text", clip=top_rect, sort=True).strip()
        bottom_text = page.get_text("text", clip=bottom_rect, sort=True).strip()

        return "\n\n".join(part for part in (top_text, bottom_text) if part).strip()


class LLMMarkdownStrategy:
    """Extractor basado en pymupdf4llm, útil para tablas/figuras complejas."""
    extractor_type = ExtractorType.LLM

    def extract(self, doc, page, page_index, analysis) -> str:
        markdown = pymupdf4llm.to_markdown(
            doc,
            pages=[page_index],
            write_images=False,
            show_progress=False,
        )
        return markdown.strip()


# Registro: agregar un extractor nuevo = agregar una entrada aquí.
_STRATEGIES: dict[ExtractorType, ExtractionStrategy] = {
    ExtractorType.TEXT: TextStrategy(),
    ExtractorType.SORT: SortStrategy(),
    ExtractorType.TEXT_REGION: TextRegionStrategy(),
    ExtractorType.LLM: LLMMarkdownStrategy(),
}


def extract_with_strategy(
    doc: "pymupdf.Document",
    page: "pymupdf.Page",
    page_index: int,
    analysis: PageAnalysis,
) -> tuple[str, ExtractorType]:
    """
    Ejecuta la estrategia recomendada por el analizador. Si la extracción
    falla (excepción) o devuelve vacío, cae a TEXT como fallback — igual
    que el comportamiento original, pero ahora aislado por página: un
    fallo aquí nunca interrumpe el resto del documento ni del lote.
    """
    strategy = _STRATEGIES.get(analysis.extractor)

    if strategy is None:
        logger.warning("Extractor desconocido '%s', usando TEXT", analysis.extractor)
        strategy = _STRATEGIES[ExtractorType.TEXT]

    try:
        text = strategy.extract(doc, page, page_index, analysis)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Fallo en extractor %s (página %s): %s. Cayendo a TEXT.",
            analysis.extractor, page_index + 1, exc,
        )
        text = ""

    if not text.strip():
        try:
            text = page.get_text("text").strip()
        except Exception:  # noqa: BLE001
            text = ""
        return text, ExtractorType.TEXT_FALLBACK

    return text, strategy.extractor_type
