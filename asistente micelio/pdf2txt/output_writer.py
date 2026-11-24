"""
output_writer.py
-----------------
Igual que el original en espíritu (escribe el .txt final y el CSV de
diagnóstico), pero el diagnóstico ahora incluye las columnas de control
de calidad y si se recurrió a OCR, que es la parte que faltaba en la
versión original.
"""

from __future__ import annotations

import csv
from pathlib import Path

from domain import DocumentResult, PageResult


def save_text(output_path: Path, pages: list[PageResult]) -> None:
    with open(output_path, "w", encoding="utf-8") as file:
        for page in pages:
            if page.text:
                file.write(page.text.strip())
            file.write("\n\n")


def build_diagnostic_row(filename: str, page: PageResult) -> dict:
    analysis = page.analysis
    quality = page.quality

    return {
        "archivo": filename,
        "pagina": page.page_number,
        "extractor_final": page.extractor_used.value if page.extractor_used else "",
        "extractor_recomendado": analysis.extractor.value if analysis else "",
        "complejidad": analysis.complejidad if analysis else "",
        "columnas_detectadas": analysis.columnas if analysis else 1,
        "bloques": analysis.bloques if analysis else 0,
        "imagenes": analysis.imagenes if analysis else 0,
        "cambios_columna": analysis.cambios_columna if analysis else 0,
        "retrocesos_y": analysis.retrocesos_y if analysis else 0,
        "tiene_tabla": analysis.tiene_tabla if analysis else False,
        "tiene_figura": analysis.tiene_figura if analysis else False,
        "tiene_lista": analysis.tiene_lista if analysis else False,
        "region_dividida": analysis.tiene_region_dividida if analysis else False,
        "split_y": analysis.split_y if analysis else "",
        "ocr_usado": page.ocr_used,
        "calidad_estado": quality.status.value if quality else "",
        "calidad_aprobada": quality.passed if quality else False,
        "calidad_caracteres": quality.char_count if quality else 0,
        "calidad_ratio_imprimible": (
            round(quality.printable_ratio, 3) if quality else ""
        ),
        "calidad_mojibake_score": (
            round(quality.mojibake_score, 3) if quality else ""
        ),
        "calidad_detalle": quality.details if quality else "",
        "error": page.error or "",
    }


DIAGNOSTIC_FIELDNAMES = [
    "archivo", "pagina", "extractor_final", "extractor_recomendado",
    "complejidad", "columnas_detectadas", "bloques", "imagenes",
    "cambios_columna", "retrocesos_y", "tiene_tabla", "tiene_figura",
    "tiene_lista", "region_dividida", "split_y", "ocr_usado",
    "calidad_estado", "calidad_aprobada", "calidad_caracteres",
    "calidad_ratio_imprimible", "calidad_mojibake_score",
    "calidad_detalle", "error",
]


def save_diagnostic(output_path: Path, rows: list[dict]) -> None:
    with open(output_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=DIAGNOSTIC_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def save_skip_log(output_path: Path, skipped_documents: list[DocumentResult]) -> None:
    """Registra por separado los documentos que no pudieron procesarse en
    absoluto (cifrados, corruptos), para que no se pierdan silenciosamente
    entre las filas de páginas del CSV principal."""
    with open(output_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=["archivo", "issue", "detalle"])
        writer.writeheader()
        for doc in skipped_documents:
            writer.writerow({
                "archivo": doc.filename,
                "issue": doc.profile.issue.value,
                "detalle": doc.skip_reason or doc.profile.error_message or "",
            })
