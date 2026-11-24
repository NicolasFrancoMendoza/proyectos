"""
ocr/providers.py
-----------------
Implementaciones concretas de `OCRProvider`. Cada una importa sus
dependencias de forma perezosa (dentro de `__init__`), de modo que si
una librería no está instalada, el pipeline principal no se rompe:
simplemente ese proveedor no estará disponible y el registry lo
reportará con un error claro en vez de un ImportError a mitad de main.py.

Proveedores incluidos:

- TesseractOCRProvider: local, gratis, rápido. Buena opción de primer
  intento para texto simple.
- PaddleOCRProvider: local, gratis, mejor manejo de layout/tablas que
  Tesseract. RECOMENDADO como motor principal para documentos
  bancarios/crediticios sensibles, porque nunca sale del equipo/red local.
- ClaudeVisionOCRProvider: cloud, de pago, máxima flexibilidad semántica
  (puede seguir instrucciones como "transcribe solo el cuerpo del texto,
  ignora encabezados repetidos"). Pensado para documentos NO sensibles
  (p. ej. material de investigación etnográfica), nunca activado por
  defecto.
"""

from __future__ import annotations

import base64
import logging
import os

from ocr.base import OCRResult

logger = logging.getLogger("pdf2text.ocr")


class TesseractOCRProvider:
    name = "tesseract"

    def __init__(self, lang: str = "spa") -> None: #spa es el idioma por defecto, pero se puede cambiar con la variable de entorno TESSERACT_LANG
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "TesseractOCRProvider requiere `pytesseract` y `Pillow` "
                "(pip install pytesseract pillow) y el binario de Tesseract "
                "instalado en el sistema."
            ) from exc
        self._pytesseract = pytesseract
        self._Image = Image
        self.lang = lang

    def extract_text_from_image(self, image_bytes: bytes) -> OCRResult:
        import io

        image = self._Image.open(io.BytesIO(image_bytes))
        text = self._pytesseract.image_to_string(image, lang=self.lang)
        return OCRResult(text=text.strip(), provider_name=self.name)


class PaddleOCRProvider:
    """
    Motor local recomendado por defecto.

    PaddleOCR cambió su API de forma incompatible entre la serie 2.x y la
    serie 3.x (lanzada en 2025): se eliminaron los parámetros
    `use_angle_cls` y `show_log` del constructor, el método `.ocr()`
    devuelve ahora objetos tipo diccionario con la clave `rec_texts` en
    vez de listas anidadas de `(caja, (texto, confianza))`, y el método
    recomendado pasó a ser `.predict()`.

    Para no depender de que el usuario tenga una versión específica,
    esta clase detecta en tiempo de ejecución qué API expone la versión
    instalada (inspeccionando la firma real de `PaddleOCR.__init__`) y
    adapta tanto la inicialización como la lectura del resultado.
    """

    name = "paddleocr"

    def __init__(self, lang: str = "es") -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCRProvider requiere `paddleocr` "
                "(pip install paddleocr paddlepaddle)."
            ) from exc

        import inspect

        init_params = inspect.signature(PaddleOCR.__init__).parameters

        try:
            if "use_angle_cls" in init_params:
                # API clásica (PaddleOCR < 3.0).
                self._engine = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
                self._api_version = "legacy"
            else:
                # API nueva (PaddleOCR >= 3.0): use_angle_cls/show_log ya no existen.
                self._engine = PaddleOCR(lang=lang)
                self._api_version = "v3"
        except Exception as exc:
            # PaddleOCR >= 3.x descarga sus modelos la primera vez desde un
            # repositorio externo (HuggingFace, ModelScope, AIStudio o BOS).
            # En redes corporativas/bancarias con firewall restrictivo esto
            # falla con un mensaje de conectividad, no con un bug del código.
            # Lo detectamos para dar una salida clara en vez de un error
            # genérico que obligue a depurar desde cero.
            message = str(exc).lower()
            network_markers = (
                "model hosting", "model hoster", "connection", "resolve",
                "network", "timed out", "name or service not known",
            )
            if any(marker in message for marker in network_markers):
                raise RuntimeError(
                    "PaddleOCR no pudo descargar sus modelos (requiere acceso "
                    "saliente a huggingface.co, modelscope.cn, aistudio.baidu.com "
                    "o paddle-model-ecology.bj.bcebos.com la primera vez que se "
                    "usa). Esto es típico en redes corporativas con firewall "
                    "restrictivo. Usa OCR_PROVIDER=tesseract en su lugar: corre "
                    "100% local, sin descargas, y ya fue validado en este "
                    "proyecto."
                ) from exc
            raise

        logger.info("PaddleOCR inicializado (API detectada: %s).", self._api_version)

    def extract_text_from_image(self, image_bytes: bytes) -> OCRResult:
        import io

        import numpy as np
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        array = np.array(image)

        if self._api_version == "v3":
            results = self._engine.predict(array)
            lines: list[str] = []
            for res in results:
                # El objeto de resultado se comporta como un dict
                # (soporta res["rec_texts"]); usamos .get() cuando está
                # disponible y, si no, indexado directo como respaldo.
                rec_texts = (
                    res.get("rec_texts", []) if hasattr(res, "get") else res["rec_texts"]
                )
                lines.extend(rec_texts)
            text = "\n".join(lines)
        else:
            result = self._engine.ocr(array, cls=True)
            lines = []
            for block in result or []:
                for _, (line_text, confidence) in block:
                    lines.append(line_text)
            text = "\n".join(lines)

        return OCRResult(text=text.strip(), provider_name=self.name)


class ClaudeVisionOCRProvider:
    """
    Proveedor cloud opcional basado en un modelo con visión. Requiere
    ANTHROPIC_API_KEY en el entorno. Pensado SOLO para documentos no
    sensibles, activado explícitamente vía configuración — nunca por
    defecto en un flujo que toque datos bancarios/crediticios.
    """

    name = "claude_vision"

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "ClaudeVisionOCRProvider requiere `anthropic` (pip install anthropic)."
            ) from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY no configurada; no se puede usar "
                "ClaudeVisionOCRProvider."
            )

        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_text_from_image(self, image_bytes: bytes) -> OCRResult:
        encoded = base64.b64encode(image_bytes).decode("utf-8")

        response = self._client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": encoded,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Transcribe únicamente el texto visible en esta "
                                "imagen, preservando el orden de lectura natural. "
                                "No agregues comentarios ni descripciones."
                            ),
                        },
                    ],
                }
            ],
        )

        text_parts = [block.text for block in response.content if block.type == "text"]
        return OCRResult(text="\n".join(text_parts).strip(), provider_name=self.name)
