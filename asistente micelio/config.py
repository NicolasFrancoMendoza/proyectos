from pathlib import Path


# ---------------------------------------------------------
# Rutas
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "data"

OUTPUT_DIR = BASE_DIR / "outputs"

DIAGNOSTIC_DIR = OUTPUT_DIR / "diagnostico"

TEXT_OUTPUT_DIR = OUTPUT_DIR / "texto_final"


# ---------------------------------------------------------
# Configuración geométrica
# ---------------------------------------------------------

MIN_BLOCKS_FOR_COLUMNS = 6

COLUMN_GAP_RATIO = 0.10

MIN_COLUMN_SEPARATION_RATIO = 0.06

FULL_WIDTH_RATIO = 0.78

MIN_BLOCKS_PER_COLUMN = 3


# ---------------------------------------------------------
# Configuración de páginas divididas
# ---------------------------------------------------------

# Mínimo de bloques de texto que debe haber
# en cada región para considerar que existen
# dos páginas lógicas.
MIN_BLOCKS_PER_REGION = 3

# Espacio vertical mínimo entre las dos regiones,
# expresado como proporción de la altura de la página.
MIN_REGION_GAP_RATIO = 0.025

# La región superior/inferior debe ocupar al menos
# este porcentaje de la altura útil de la página.
MIN_REGION_HEIGHT_RATIO = 0.25

# Evita considerar como "página dividida" una página
# donde simplemente existe un bloque aislado arriba
# o abajo.
REGION_BALANCE_RATIO = 0.25


# ---------------------------------------------------------
# Configuración de retrocesos
# ---------------------------------------------------------

MIN_VERTICAL_TOLERANCE = 10

MEDIAN_HEIGHT_MULTIPLIER = 1.5


# ---------------------------------------------------------
# Configuración de complejidad
# ---------------------------------------------------------

HIGH_SWITCHES = 5

HIGH_BACKTRACKS = 3

SORT_SWITCHES = 4

SORT_BACKTRACKS = 2


# ---------------------------------------------------------
# Crear directorios
# ---------------------------------------------------------

OUTPUT_DIR.mkdir(exist_ok=True)

DIAGNOSTIC_DIR.mkdir(exist_ok=True)

TEXT_OUTPUT_DIR.mkdir(exist_ok=True)