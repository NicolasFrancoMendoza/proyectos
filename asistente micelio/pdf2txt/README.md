# pdf2text — arquitectura revisada

## Qué cambió respecto a la versión original

| Problema original | Solución |
|---|---|
| Sin clasificación previa → PDFs cifrados/corruptos/escaneados rompían el flujo o producían basura silenciosa | `classification/inspector.py`: inspecciona cada PDF antes de extraer y genera un `DocumentProfile` |
| Sin control de calidad del `.txt` de salida | `validation/quality_gate.py`: longitud mínima, ratio imprimible, mojibake, caracteres de reemplazo |
| `extract_page()` con `if/elif` acoplado | `extraction/strategies.py`: cada extractor es una clase (Strategy pattern) |
| Sin soporte de OCR, antes atado a Gemini | `ocr/`: `Protocol` + registry + feature flag — se activa/cambia/elimina sin tocar el resto del código |
| `print()`, un solo `try/except` por archivo | `logging` estructurado; cada página se procesa aislada, el lote nunca se detiene |

## Uso

```bash
pip install -r requirements.txt
python main.py
```

Coloca los PDFs en `data/`. Salidas en `outputs/texto_final/*.txt` y
diagnóstico en `outputs/diagnostico/orden_lectura_final.csv` (por página)
y `outputs/diagnostico/documentos_omitidos.csv` (documentos que no se
pudieron procesar en absoluto: cifrados, corruptos).

## Activar el módulo OCR (desactivado por defecto)

```bash
# Local, recomendado para documentos sensibles (bancarios/crediticios):
pip install paddleocr paddlepaddle
export OCR_PROVIDER=paddleocr
python main.py

# Alternativa local más liviana:
pip install pytesseract pillow   # + binario tesseract-ocr del sistema
export OCR_PROVIDER=tesseract

# Cloud (solo para contenido NO sensible, p. ej. investigación de campo):
pip install anthropic
export ANTHROPIC_API_KEY=sk-...
export OCR_PROVIDER=claude_vision
```

El OCR solo se invoca cuando una página falla el control de calidad
(`validation/quality_gate.py`) y hay un proveedor activo. Para
desactivarlo del todo, basta con no definir `OCR_PROVIDER` (o ponerlo en
`none`) — incluso se puede borrar la carpeta `ocr/` sin que `pipeline.py`
deje de funcionar, porque la importa de forma perezosa.

## Agregar un extractor de texto nuevo

1. Crear una clase en `extraction/strategies.py` que implemente
   `extract(self, doc, page, page_index, analysis) -> str`.
2. Agregarla al diccionario `_STRATEGIES`.
3. Si aplica, agregar el valor correspondiente a `ExtractorType` en
   `domain.py` y a la lógica de `choose_extractor()` en
   `extraction/page_analyzer.py`.

## Agregar un proveedor OCR nuevo

1. Crear una clase en `ocr/providers.py` que implemente `OCRProvider`
   (`extract_text_from_image(image_bytes) -> OCRResult`), con imports
   perezosos dentro de `__init__`.
2. Registrar su factory en `_PROVIDER_FACTORIES` en `ocr/registry.py`.
