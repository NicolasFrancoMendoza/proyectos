# Pipeline de extracción PDF → TXT

Pipeline modular para extraer texto de documentos PDF preservando, en la medida de lo posible, el **orden natural de lectura** del documento.

El sistema analiza cada página individualmente y selecciona automáticamente un método de extracción según su estructura.

---

## 1. Objetivo

El objetivo principal del proyecto es convertir documentos PDF en archivos `.txt` utilizables posteriormente por procesos de análisis, búsqueda, clasificación o modelos de lenguaje.

El sistema busca resolver especialmente estos problemas:

- PDFs con texto normal.
- PDFs con dos columnas.
- PDFs con una página física que contiene dos regiones o páginas lógicas.
- Páginas con tablas, figuras o listas.
- Documentos con estructuras complejas.
- Mantener el orden de lectura original siempre que sea posible.
- Evitar utilizar LLM cuando la extracción nativa del PDF es suficiente.

### Principio principal

> **Primero confiar en el orden nativo del PDF. Solo aplicar procesamiento adicional cuando exista evidencia de que es necesario.**

Esto es importante porque algunos documentos tienen una diagramación visual compleja que no debe interpretarse necesariamente como un problema de orden de lectura.

---

# 2. Arquitectura

El proyecto está dividido en módulos:

```text
proyecto/
│
├── main.py
├── config.py
├── pdf_reader.py
├── page_analyzer.py
├── extractor.py
├── output_writer.py
│
├── data/
│   └── *.pdf
│
└── outputs/
    ├── texto_final/
    │   └── *.txt
    │
    └── diagnostico/
        └── orden_lectura_final.csv
```

### Flujo general

```text
PDF
 │
 ▼
pdf_reader.py
 │
 ├── obtiene bloques de texto
 ├── normaliza información
 ├── detecta columnas
 └── detecta regiones verticales
 │
 ▼
page_analyzer.py
 │
 └── decide extractor
 │
 ▼
extractor.py
 │
 ├── TEXT
 ├── TEXT_REGION
 └── LLM
 │
 ▼
output_writer.py
 │
 ├── TXT final
 └── CSV diagnóstico
```

---

# 3. Módulos

## `main.py`

Es el punto de entrada del programa.

Responsabilidades:

1. Buscar PDFs dentro de `data/`.
2. Abrir cada PDF.
3. Procesar cada página.
4. Obtener los bloques de texto.
5. Analizar la estructura de cada página.
6. Ejecutar el extractor recomendado.
7. Guardar el texto final.
8. Generar el diagnóstico CSV.

Se ejecuta con:

```bash
python main.py
```

---

# 4. `config.py`

Contiene las configuraciones globales del sistema.

Actualmente incluye:

```python
MIN_BLOCKS_FOR_COLUMNS = 6

COLUMN_GAP_RATIO = 0.10

MIN_COLUMN_SEPARATION_RATIO = 0.06

FULL_WIDTH_RATIO = 0.78

MIN_BLOCKS_PER_COLUMN = 3
```

Estas variables controlan la detección de columnas.

También existen parámetros para detectar regiones verticales:

```python
MIN_BLOCKS_PER_REGION = 3

MIN_REGION_GAP_RATIO = 0.025

MIN_REGION_HEIGHT_RATIO = 0.25

REGION_BALANCE_RATIO = 0.25
```

Y parámetros utilizados para analizar posibles problemas de orden:

```python
MIN_VERTICAL_TOLERANCE = 10

MEDIAN_HEIGHT_MULTIPLIER = 1.5

HIGH_SWITCHES = 5

HIGH_BACKTRACKS = 3

SORT_SWITCHES = 4

SORT_BACKTRACKS = 2
```

### Importante

No modificar estos valores sin revisar primero el diagnóstico generado por el sistema.

---

# 5. `pdf_reader.py`

Se encarga de leer la estructura interna del PDF.

## Funciones principales

### `open_pdf()`

Abre un documento PDF mediante PyMuPDF.

```python
open_pdf(path)
```

---

### `get_blocks()`

Obtiene los bloques de texto de una página.

Cada bloque contiene información como:

```text
x0
y0
x1
y1
cx
cy
width
height
text
index
```

Esta información permite analizar la posición del texto dentro de la página.

---

### `normalize()`

Normaliza el texto utilizado para análisis.

Por ejemplo:

- elimina espacios innecesarios;
- normaliza saltos de línea;
- elimina líneas vacías innecesarias.

La normalización se utiliza principalmente para diagnóstico y análisis, no para reemplazar el texto final extraído.

---

### `detect_columns()`

Determina si una página parece tener:

```text
1 columna
```

o

```text
2 columnas
```

La detección se basa en la distribución horizontal de los bloques.

No significa que el documento tenga necesariamente una estructura editorial de dos columnas; únicamente indica que los bloques de texto presentan una separación horizontal compatible con dos regiones.

---

### `detect_split_regions()`

Busca páginas físicas que parecen contener dos regiones verticales independientes.

Ejemplo conceptual:

```text
┌───────────────────────┐
│                       │
│      REGIÓN 1         │
│                       │
├───────────────────────┤
│                       │
│      REGIÓN 2         │
│                       │
└───────────────────────┘
```

Cuando se detecta esta estructura, el extractor puede procesar primero la región superior y posteriormente la inferior.

---

# 6. `page_analyzer.py`

Es el módulo que toma las características de una página y decide cómo debe extraerse.

Analiza:

- número de bloques;
- columnas;
- cambios de columna;
- retrocesos verticales;
- tablas;
- figuras;
- listas;
- regiones verticalmente divididas.

---

# 7. Estrategia actual de extracción

La lógica actual es deliberadamente conservadora.

## Prioridad 1 — Región vertical

Si se detecta una división física de la página:

```text
TEXT_REGION
```

Se procesa primero la región superior y después la inferior.

Esto busca resolver documentos donde una página física contiene dos espacios lógicos independientes.

---

## Prioridad 2 — Dos columnas

Si se detectan dos columnas:

```text
TEXT
```

### ¿Por qué no `SORT`?

Porque las pruebas anteriores demostraron que el método utilizado por la versión V2 del proyecto:

```python
page.get_text("text")
```

proporcionaba un orden útil para determinados documentos complejos.

El sistema no debe asumir que una reorganización geométrica mediante:

```python
page.get_text("text", sort=True)
```

es necesariamente mejor.

Por lo tanto:

> **Dos columnas no implica automáticamente utilizar `SORT` ni LLM.**

---

## Prioridad 3 — Página compleja

Si la página no es una página de dos columnas ni una región vertical y contiene estructuras que justifican un análisis más complejo, puede utilizarse:

```text
LLM
```

Actualmente las señales principales son:

- tablas;
- figuras.

---

## Prioridad 4 — Página normal

En ausencia de estructuras especiales:

```text
TEXT
```

---

# 8. Regla resumida

La lógica puede representarse así:

```text
                 ┌─────────────────┐
                 │      PDF        │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Analizar página │
                 └────────┬────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
       ¿Región vertical?              │
              │                       │
          SÍ  ▼                       │ NO
       TEXT_REGION                    │
                                      ▼
                              ¿Dos columnas?
                                      │
                              ┌───────┴───────┐
                              │               │
                             SÍ              NO
                              │               │
                              ▼               ▼
                            TEXT       ¿Tabla/Figura?
                                              │
                                      ┌───────┴───────┐
                                      │               │
                                     SÍ              NO
                                      │               │
                                      ▼               ▼
                                     LLM             TEXT
```

---

# 9. `extractor.py`

Contiene las implementaciones concretas de extracción.

## `extract_text()`

Utiliza:

```python
page.get_text("text")
```

Es el extractor principal.

Es importante porque utiliza el orden de texto proporcionado por el propio PDF.

---

## `extract_sorted()`

Utiliza:

```python
page.get_text(
    "text",
    sort=True
)
```

Actualmente existe como extractor disponible pero **no es la opción predeterminada**.

Debe utilizarse solamente si posteriormente las pruebas demuestran que mejora determinados tipos de documentos.

---

## `extract_text_region()`

Divide una página según una coordenada vertical:

```text
REGIÓN SUPERIOR
        ↓
REGIÓN INFERIOR
```

Cada región se extrae independientemente.

Después se combinan:

```text
texto región superior

texto región inferior
```

---

## `extract_llm()`

Utiliza:

```python
pymupdf4llm.to_markdown()
```

El objetivo es utilizarlo solamente cuando la estructura de la página sea suficientemente compleja como para justificar una interpretación adicional.

### Limitación

El resultado de PyMuPDF4LLM está orientado a Markdown y puede intentar reconstruir:

- tablas;
- listas;
- encabezados;
- columnas;
- estructuras visuales.

Esto puede ser contraproducente cuando el objetivo es preservar el orden textual original.

Por esta razón:

> **LLM no debe utilizarse como extractor predeterminado.**

---

# 10. `output_writer.py`

Gestiona los archivos generados.

## Texto final

Los documentos se guardan como:

```text
outputs/texto_final/nombre_documento.txt
```

El formato es **TXT plano**.

No se generan encabezados Markdown como:

```text
# Documento

## Página 4
```

El objetivo es que el archivo contenga directamente el texto extraído.

---

# 11. Diagnóstico

Se genera:

```text
outputs/diagnostico/orden_lectura_final.csv
```

Contiene información por página.

Campos principales:

```text
archivo
pagina
extractor_final
extractor_recomendado
complejidad
columnas_detectadas
bloques
imagenes
cambios_columna
retrocesos_y
tiene_tabla
tiene_figura
tiene_lista
region_dividida
split_y
```

---

# 12. Interpretación del diagnóstico

Ejemplo:

```text
pagina: 5
extractor_final: TEXT
extractor_recomendado: TEXT
columnas_detectadas: 2
```

Significa:

- se detectaron dos regiones horizontales;
- se decidió conservar el orden nativo del PDF;
- no se utilizó LLM.

Otro ejemplo:

```text
pagina: 22
extractor_final: TEXT_REGION
region_dividida: True
split_y: 248.44
```

Significa que la página fue considerada físicamente dividida en dos regiones y se extrajo cada región independientemente.

---

# 13. Dependencias

El proyecto utiliza principalmente:

```text
PyMuPDF
PyMuPDF4LLM
```

Instalación:

```bash
pip install pymupdf pymupdf4llm
```

Comprobar versiones:

```bash
pip show pymupdf
pip show pymupdf4llm
```

---

# 14. Ejecución

Colocar los PDFs dentro de:

```text
data/
```

Ejemplo:

```text
data/
├── documento_1.pdf
├── documento_2.pdf
└── documento_3.pdf
```

Ejecutar:

```bash
python main.py
```

Los resultados aparecerán en:

```text
outputs/
├── texto_final/
└── diagnostico/
```

---

# 15. Filosofía de mantenimiento

El proyecto debe seguir una estrategia de **mínima intervención**.

No agregar reglas únicamente porque una página parezca visualmente compleja.

La pregunta correcta es:

> ¿El método actual produce un orden de lectura incorrecto?

Si la respuesta es no, no debe aplicarse otro extractor.

---

## Prioridad de métodos

Actualmente:

```text
TEXT
  ↓
TEXT_REGION
  ↓
LLM
```

No significa que LLM sea menos potente.

Significa que debe utilizarse únicamente cuando el método más sencillo no sea suficiente.

---

# 16. Por qué se eliminó el uso indiscriminado de LLM

En versiones anteriores se utilizaba una lógica similar a:

```python
if tiene_tabla:
    return "LLM"

if tiene_figura:
    return "LLM"

if tiene_lista:
    return "LLM"
```

Esto generaba problemas.

Por ejemplo, una página podía contener:

```text
dos columnas
+
números de sección
+
una tabla
```

y terminar automáticamente en:

```text
LLM
```

aunque el orden nativo del PDF ya fuera correcto.

Esto se observó especialmente en páginas complejas del documento:

```text
9. Acuerdo_Final_de_Paz_2018.pdf
```

incluyendo las páginas físicas 4, 5 y 6.

El problema no era necesariamente la extracción del texto, sino la **reconstrucción artificial de la estructura visual por parte del LLM**.

---

# 17. Limitaciones actuales

## 17.1 Detección de columnas

La detección es heurística.

Puede producir falsos positivos cuando un documento contiene:

- bloques muy separados;
- títulos;
- cuadros;
- elementos gráficos;
- encabezados laterales.

---

## 17.2 Detección de regiones verticales

También es heurística.

Una gran separación vertical entre bloques puede parecer una división de página aunque sea simplemente:

- un espacio editorial;
- una imagen;
- un título;
- una sección;
- una página parcialmente vacía.

Por eso los parámetros deben ajustarse con datos reales.

---

## 17.3 LLM

El extractor LLM puede modificar la estructura original.

Puede:

- crear tablas Markdown;
- modificar saltos;
- reconstruir columnas;
- interpretar listas;
- reorganizar elementos.

Por lo tanto, no debe considerarse automáticamente superior a la extracción nativa.

---

## 17.4 Tablas

El sistema todavía no posee un detector geométrico especializado de tablas.

La detección actual se basa parcialmente en señales textuales como:

```text
tabla
cuadro
columnas
filas
```

Esto puede producir falsos positivos.

---

## 17.5 Diagnóstico comparativo

Los campos:

```text
palabras_original
palabras_sort
palabras_llm
```

todavía no representan una comparación real entre los tres extractores.

Actualmente permanecen reservados para una futura etapa de evaluación.

---

# 18. Próxima etapa de desarrollo

Una vez estabilizado el orden de lectura, el siguiente paso recomendado es convertir el diagnóstico en un sistema de evaluación real.

Para cada página se podría calcular:

```text
TEXT
SORT
LLM
```

y comparar:

- cantidad de palabras;
- cantidad de líneas;
- texto perdido;
- duplicación;
- cambios de orden;
- contenido vacío;
- diferencias entre extractores.

Esto permitiría decidir automáticamente cuándo un extractor alternativo realmente aporta una mejora.

---

# 19. Principio fundamental del proyecto

La arquitectura debe mantenerse bajo esta regla:

> **No intentar reconstruir la página si el PDF ya proporciona un orden de lectura correcto.**

En términos prácticos:

```text
PDF bien estructurado
        ↓
     TEXT
        ↓
   conservarlo
```

Solo cuando exista evidencia de un problema:

```text
PDF problemático
        ↓
analizar estructura
        ↓
TEXT_REGION / LLM
```

El objetivo no es obtener la extracción visualmente más sofisticada.

El objetivo es obtener **el texto correcto, en el orden correcto, con la menor cantidad posible de transformaciones artificiales**.