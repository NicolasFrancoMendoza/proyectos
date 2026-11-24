"""
domain.py
---------
Contratos de datos compartidos entre todas las etapas del pipeline.
Ningún módulo de negocio debería construir diccionarios "a mano": todos
pasan por estas dataclasses, lo que permite tipado estático y evita el
acoplamiento silencioso por claves de diccionario (como en el código
original, donde `analysis.get("extractor")` podía fallar en silencio).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ExtractorType(str, Enum):
    TEXT = "TEXT"
    SORT = "SORT"
    TEXT_REGION = "TEXT_REGION"
    LLM = "LLM"
    OCR = "OCR"
    TEXT_FALLBACK = "TEXT_FALLBACK"


class DocumentIssue(str, Enum):
    """Problemas detectados ANTES de intentar extraer texto."""
    NONE = "NONE"
    ENCRYPTED = "ENCRYPTED"
    CORRUPTED = "CORRUPTED"
    SCANNED_IMAGE_ONLY = "SCANNED_IMAGE_ONLY"
    EMPTY = "EMPTY"


class QualityStatus(str, Enum):
    """Resultado del control de calidad posterior a la extracción."""
    OK = "OK"
    LOW_LENGTH = "LOW_LENGTH"
    LOW_PRINTABLE_RATIO = "LOW_PRINTABLE_RATIO"
    MOJIBAKE_DETECTED = "MOJIBAKE_DETECTED"
    REPLACEMENT_CHARS = "REPLACEMENT_CHARS"
    EMPTY_OUTPUT = "EMPTY_OUTPUT"
    FAILED = "FAILED"


@dataclass
class PageClassification:
    """Salida de la etapa de clasificación, por página."""
    page_number: int
    is_image_only: bool = False
    image_coverage_ratio: float = 0.0
    char_count: int = 0


@dataclass
class DocumentProfile:
    """Salida de la etapa de clasificación, a nivel de documento."""
    path: Path
    issue: DocumentIssue = DocumentIssue.NONE
    is_encrypted: bool = False
    page_count: int = 0
    pages: list[PageClassification] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def is_processable(self) -> bool:
        return self.issue not in (DocumentIssue.ENCRYPTED, DocumentIssue.CORRUPTED)


@dataclass
class PageAnalysis:
    """Equivalente tipado del dict que hoy devuelve `analyze_page`."""
    extractor: ExtractorType
    complejidad: str
    columnas: int
    bloques: int
    imagenes: int
    cambios_columna: int
    retrocesos_y: int
    tiene_tabla: bool
    tiene_figura: bool
    tiene_lista: bool
    tiene_region_dividida: bool
    split_y: Optional[float] = None


@dataclass
class QualityReport:
    status: QualityStatus
    char_count: int
    printable_ratio: float
    replacement_char_count: int
    mojibake_score: float
    passed: bool
    details: str = ""


@dataclass
class PageResult:
    page_number: int
    text: str
    extractor_used: ExtractorType
    analysis: Optional[PageAnalysis] = None
    quality: Optional[QualityReport] = None
    ocr_used: bool = False
    error: Optional[str] = None


@dataclass
class DocumentResult:
    filename: str
    profile: DocumentProfile
    pages: list[PageResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: Optional[str] = None
