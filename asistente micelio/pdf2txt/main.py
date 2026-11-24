"""
main.py
-------
Entry point del pipeline. Comparado con el original:

- Logging estructurado (`logging`) en vez de `print()`.
- El lote nunca se detiene: un documento cifrado/corrupto se registra en
  `documentos_omitidos.csv` y se continúa con el siguiente.
- El diagnóstico por página ahora incluye las columnas de calidad y uso
  de OCR (ver output_writer.py).
"""

from __future__ import annotations

import glob
import logging
import os
from pathlib import Path

from config import DIAGNOSTIC_DIR, INPUT_DIR, TEXT_OUTPUT_DIR
from output_writer import build_diagnostic_row, save_diagnostic, save_skip_log, save_text

try:
    from dotenv import load_dotenv
    load_dotenv()  # lee el archivo .env (si existe) y carga OCR_PROVIDER, etc.
    print("Se encontró la siguiente configuración OCR: ", os.environ.get("OCR_PROVIDER"))
except ImportError:
    print("python-dotenv no está instalado: se usarán variables de entorno del sistema")
    pass  # python-dotenv es opcional: si no está instalado, solo se usan variables de entorno del sistema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pdf2text.main")


def main() -> None:
    from pipeline import process_document  # import diferido: evita cargar pymupdf si solo se corren tests

    pdf_files = sorted(glob.glob(str(INPUT_DIR / "*.pdf")))
    logger.info("PDF encontrados: %d", len(pdf_files))

    diagnostic_rows: list[dict] = []
    skipped_documents = []
    processed_count = 0

    for pdf_path in pdf_files:
        path = Path(pdf_path)
        try:
            result = process_document(path)
        except Exception as exc:  # noqa: BLE001 - última red de seguridad del lote
            logger.error("Error no controlado procesando %s: %s", path.name, exc)
            continue

        if result.skipped:
            skipped_documents.append(result)
            continue

        for page in result.pages:
            diagnostic_rows.append(build_diagnostic_row(result.filename, page))

        output_path = TEXT_OUTPUT_DIR / f"{path.stem}.txt"
        save_text(output_path, result.pages)
        processed_count += 1

    diagnostic_path = DIAGNOSTIC_DIR / "orden_lectura_final.csv"
    save_diagnostic(diagnostic_path, diagnostic_rows)

    skip_log_path = DIAGNOSTIC_DIR / "documentos_omitidos.csv"
    save_skip_log(skip_log_path, skipped_documents)

    logger.info("=" * 60)
    logger.info("PROCESAMIENTO TERMINADO")
    logger.info("=" * 60)
    logger.info("Documentos procesados: %d", processed_count)
    logger.info("Documentos omitidos: %d", len(skipped_documents))
    logger.info("Páginas procesadas: %d", len(diagnostic_rows))
    logger.info("Diagnóstico: %s", diagnostic_path)
    logger.info("Documentos omitidos (detalle): %s", skip_log_path)
    logger.info("Textos finales: %s", TEXT_OUTPUT_DIR)

    if os.environ.get("OCR_PROVIDER", "none") == "none":
        logger.info(
            "Nota: módulo OCR desactivado. Actívalo con la variable de entorno "
            "OCR_PROVIDER=paddleocr (recomendado) para procesar páginas escaneadas."
        )


if __name__ == "__main__":
    main()
