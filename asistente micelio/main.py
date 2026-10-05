import glob
import os

from config import (
    INPUT_DIR,
    DIAGNOSTIC_DIR,
    TEXT_OUTPUT_DIR,
)

from pdf_reader import (
    open_pdf,
    get_blocks,
)

from page_analyzer import (
    analyze_page,
)

from extractor import (
    extract_page,
)

from output_writer import (
    save_text,
    save_diagnostic,
    build_diagnostic_row,
)


def process_pdf(
    pdf_path,
    diagnostic_rows,
):

    filename = os.path.basename(
        pdf_path
    )

    print(
        f"\nProcesando: {filename}"
    )

    doc = open_pdf(
        pdf_path
    )

    pages = []

    for page_index, page in enumerate(
        doc
    ):

        page_number = page_index + 1

        blocks = get_blocks(
            page
        )

        analysis = analyze_page(
            page,
            blocks,
        )

        extractor = analysis[
            "extractor"
        ]

        extracted = extract_page(
            doc,
            page,
            page_index,
            extractor,
            analysis,
        )

        pages.append(
            (
                page_number,
                extracted["text"],
            )
        )

        diagnostic_rows.append(
            build_diagnostic_row(
                filename,
                page_number,
                analysis,
                extracted,
            )
        )

        print(
            f"  Página {page_number}: "
            f"{extractor} / "
            f"{analysis['complejidad']}"
        )

    doc.close()

    output_path = (
        TEXT_OUTPUT_DIR
        / f"{os.path.splitext(filename)[0]}.txt"
    )

    save_text(
        output_path,
        filename,
        pages,
    )


def main():

    pdf_files = sorted(
        glob.glob(
            str(
                INPUT_DIR / "*.pdf"
            )
        )
    )

    print(
        f"PDF encontrados: "
        f"{len(pdf_files)}"
    )

    diagnostic_rows = []

    for pdf_path in pdf_files:

        try:

            process_pdf(
                pdf_path,
                diagnostic_rows,
            )

        except Exception as error:

            print(
                f"\nERROR procesando "
                f"{pdf_path}: {error}"
            )

    diagnostic_path = (
        DIAGNOSTIC_DIR
        / "orden_lectura_final.csv"
    )

    save_diagnostic(
        diagnostic_path,
        diagnostic_rows,
    )

    print("\n")
    print("=" * 60)
    print(
        "PROCESAMIENTO TERMINADO"
    )
    print("=" * 60)

    print(
        f"Páginas procesadas: "
        f"{len(diagnostic_rows)}"
    )

    print(

        
        f"Diagnóstico: "
        f"{diagnostic_path}"
    )

    print(
        f"Textos finales: "
        f"{TEXT_OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()