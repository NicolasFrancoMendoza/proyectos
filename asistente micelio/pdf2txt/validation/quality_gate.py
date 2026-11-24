"""
validation/quality_gate.py
---------------------------
Etapa 3 del pipeline: valida que el texto extraído sea USABLE, no solo
"no vacío". El código original nunca verificaba esto — una página podía
extraerse con el extractor "correcto" y aun así producir basura
(mojibake, texto truncado, relleno de símbolos) sin que el diagnóstico
lo reflejara.

Reglas aplicadas (configurables vía config.py):

1. Longitud mínima de caracteres.
2. Ratio de caracteres imprimibles/alfanuméricos sobre el total.
3. Conteo de caracteres de reemplazo Unicode (U+FFFD, '�') — señal
   directa de una mala decodificación.
4. Heurística de mojibake: secuencias típicas de una doble decodificación
   UTF-8/Latin-1 (p. ej. "Ã©", "Ã±", "â€™").
"""

from __future__ import annotations

import re
import unicodedata

from domain import QualityReport, QualityStatus

MOJIBAKE_PATTERNS = re.compile(
    r"(Ã.|â€.|Â.|Ð.|ï¿½)"
)

REPLACEMENT_CHAR = "\ufffd"


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0

    printable = sum(
        1 for ch in text
        if ch.isalnum() or ch.isspace() or unicodedata.category(ch).startswith("P")
    )
    return printable / len(text)


def _mojibake_score(text: str) -> float:
    if not text:
        return 0.0
    matches = MOJIBAKE_PATTERNS.findall(text)
    return len(matches) / max(len(text) / 100, 1)  # ocurrencias por cada ~100 chars


def evaluate_text(
    text: str,
    *,
    min_chars: int = 30,
    min_printable_ratio: float = 0.85,
    max_mojibake_score: float = 1.5,
    max_replacement_chars: int = 3,
) -> QualityReport:
    """
    Evalúa un texto extraído y devuelve un QualityReport.
    `passed=True` significa que el texto puede usarse tal cual; si es
    `False`, el pipeline puede decidir escalar a OCR (si está activo) o
    marcar la página como fallida en el diagnóstico.
    """
    if not text or not text.strip():
        return QualityReport(
            status=QualityStatus.EMPTY_OUTPUT,
            char_count=0,
            printable_ratio=0.0,
            replacement_char_count=0,
            mojibake_score=0.0,
            passed=False,
            details="Texto vacío tras la extracción.",
        )

    char_count = len(text)
    printable_ratio = _printable_ratio(text)
    replacement_count = text.count(REPLACEMENT_CHAR)
    mojibake_score = _mojibake_score(text)

    if char_count < min_chars:
        return QualityReport(
            status=QualityStatus.LOW_LENGTH,
            char_count=char_count,
            printable_ratio=printable_ratio,
            replacement_char_count=replacement_count,
            mojibake_score=mojibake_score,
            passed=False,
            details=f"Solo {char_count} caracteres (mínimo {min_chars}).",
        )

    if replacement_count > max_replacement_chars:
        return QualityReport(
            status=QualityStatus.REPLACEMENT_CHARS,
            char_count=char_count,
            printable_ratio=printable_ratio,
            replacement_char_count=replacement_count,
            mojibake_score=mojibake_score,
            passed=False,
            details=f"{replacement_count} caracteres de reemplazo U+FFFD detectados.",
        )

    if mojibake_score > max_mojibake_score:
        return QualityReport(
            status=QualityStatus.MOJIBAKE_DETECTED,
            char_count=char_count,
            printable_ratio=printable_ratio,
            replacement_char_count=replacement_count,
            mojibake_score=mojibake_score,
            passed=False,
            details=f"Puntaje de mojibake {mojibake_score:.2f} supera el umbral.",
        )

    if printable_ratio < min_printable_ratio:
        return QualityReport(
            status=QualityStatus.LOW_PRINTABLE_RATIO,
            char_count=char_count,
            printable_ratio=printable_ratio,
            replacement_char_count=replacement_count,
            mojibake_score=mojibake_score,
            passed=False,
            details=f"Ratio imprimible {printable_ratio:.2f} bajo el umbral.",
        )

    return QualityReport(
        status=QualityStatus.OK,
        char_count=char_count,
        printable_ratio=printable_ratio,
        replacement_char_count=replacement_count,
        mojibake_score=mojibake_score,
        passed=True,
    )
