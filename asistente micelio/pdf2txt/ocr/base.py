"""
ocr/base.py
-----------
Contrato mínimo que debe cumplir cualquier proveedor de OCR/VLM para
poder conectarse al pipeline. Mientras un proveedor implemente
`OCRProvider`, es intercambiable sin tocar ninguna otra parte del
sistema (Adapter pattern).

Para AÑADIR un proveedor nuevo: crear una clase que implemente este
Protocol y registrarla en `ocr/registry.py`.

Para QUITAR el módulo OCR por completo: basta con no activarlo en la
configuración (OCR_PROVIDER = "none") o incluso borrar la carpeta
`ocr/` — `pipeline.py` lo importa de forma perezosa y opcional, nunca
como dependencia dura.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class OCRResult:
    text: str
    confidence: float = 0.0
    provider_name: str = ""


class OCRProvider(Protocol):
    """Cualquier motor de OCR/VLM debe poder recibir una imagen (bytes PNG)
    y devolver texto plano."""

    name: str

    def extract_text_from_image(self, image_bytes: bytes) -> OCRResult:
        ...
