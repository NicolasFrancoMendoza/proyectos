"""
ocr/registry.py
----------------
Único punto de acoplamiento entre el pipeline principal y el módulo OCR.
`pipeline.py` nunca importa `providers.py` directamente: solo pide
`get_active_provider()`, que puede devolver `None` (OCR desactivado)
sin que el resto del sistema tenga que saberlo.

Activar/desactivar/reemplazar el motor OCR es, en consecuencia, un
cambio de UNA variable de entorno/configuración:

    OCR_PROVIDER=none          -> OCR desactivado (comportamiento actual)
    OCR_PROVIDER=tesseract     -> local, rápido, básico
    OCR_PROVIDER=paddleocr     -> local, recomendado por defecto cuando se activa
    OCR_PROVIDER=claude_vision -> cloud, solo para contenido no sensible
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from ocr.base import OCRProvider

logger = logging.getLogger("pdf2text.ocr.registry")

_PROVIDER_FACTORIES = {
    "tesseract": lambda: __import__(
    "ocr.providers", fromlist=["TesseractOCRProvider"]
    ).TesseractOCRProvider(lang=os.environ.get("TESSERACT_LANG", "spa")), #tiene configuración de IDIOMAS en .env
    "paddleocr": lambda: __import__(
        "ocr.providers", fromlist=["PaddleOCRProvider"]
    ).PaddleOCRProvider(),
    "claude_vision": lambda: __import__(
        "ocr.providers", fromlist=["ClaudeVisionOCRProvider"]
    ).ClaudeVisionOCRProvider(),
}

_cached_provider: Optional[OCRProvider] = None
_cache_initialized = False


def get_active_provider() -> Optional[OCRProvider]:
    """
    Devuelve el proveedor OCR activo según la variable de entorno
    OCR_PROVIDER, o None si está desactivado o no se pudo inicializar.

    El resultado se cachea en el proceso: el proveedor se instancia una
    sola vez (algunos, como PaddleOCR, cargan modelos pesados en memoria).
    """
    global _cached_provider, _cache_initialized

    if _cache_initialized:
        return _cached_provider

    provider_name = os.environ.get("OCR_PROVIDER", "none").strip().lower()
    _cache_initialized = True

    if provider_name in ("", "none", "off", "disabled"):
        logger.info("Módulo OCR desactivado (OCR_PROVIDER=%s).", provider_name)
        _cached_provider = None
        return None

    factory = _PROVIDER_FACTORIES.get(provider_name)
    if factory is None:
        logger.error(
            "OCR_PROVIDER='%s' no reconocido. Opciones válidas: %s. OCR desactivado.",
            provider_name, list(_PROVIDER_FACTORIES.keys()),
        )
        _cached_provider = None
        return None

    try:
        _cached_provider = factory()
        logger.info("Proveedor OCR activo: %s", provider_name)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "No se pudo inicializar el proveedor OCR '%s': %s. "
            "El pipeline continuará sin OCR.", provider_name, exc,
        )
        _cached_provider = None

    return _cached_provider


def is_ocr_enabled() -> bool:
    return get_active_provider() is not None
