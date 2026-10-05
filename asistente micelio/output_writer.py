import csv


def word_count(text):

    if not text:
        return 0

    return len(
        text.split()
    )


def save_text(
    output_path,
    filename,
    pages,
):

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        for page_number, text in pages:

            if text:

                file.write(
                    text.strip()
                )

            file.write(
                "\n\n"
            )


def build_diagnostic_row(
    filename,
    page_number,
    analysis,
    extracted,
):

    return {
        "archivo": filename,

        "pagina": page_number,

        "extractor_final": extracted.get(
            "extractor",
            "",
        ),

        "extractor_recomendado": analysis.get(
            "extractor",
            "",
        ),

        "complejidad": analysis.get(
            "complejidad",
            "",
        ),

        "columnas_detectadas": analysis.get(
            "columnas",
            1,
        ),

        "bloques": analysis.get(
            "bloques",
            0,
        ),

        "imagenes": analysis.get(
            "imagenes",
            0,
        ),

        "cambios_columna": analysis.get(
            "cambios_columna",
            0,
        ),

        "retrocesos_y": analysis.get(
            "retrocesos_y",
            0,
        ),

        "tiene_tabla": analysis.get(
            "tiene_tabla",
            False,
        ),

        "tiene_figura": analysis.get(
            "tiene_figura",
            False,
        ),

        "tiene_lista": analysis.get(
            "tiene_lista",
            False,
        ),

        "region_dividida": analysis.get(
            "tiene_region_dividida",
            False,
        ),

        "split_y": analysis.get(
            "split_y",
            "",
        ),

        "palabras_original": 0,

        "palabras_sort": 0,

        "palabras_llm": 0,
    }


def save_diagnostic(
    output_path,
    rows,
):

    fieldnames = [
        "archivo",
        "pagina",
        "extractor_final",
        "extractor_recomendado",
        "complejidad",
        "columnas_detectadas",
        "bloques",
        "imagenes",
        "cambios_columna",
        "retrocesos_y",
        "tiene_tabla",
        "tiene_figura",
        "tiene_lista",
        "region_dividida",
        "split_y",
        "palabras_original",
        "palabras_sort",
        "palabras_llm",
    ]

    with open(
        output_path,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        writer.writerows(rows)