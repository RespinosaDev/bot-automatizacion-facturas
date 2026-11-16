# Bot de automatización de facturas

Bot en **Python** que automatiza el procesamiento de facturas en PDF de principio a fin. Lee cada factura, con OCR si está escaneada, y extrae sus datos. Después valida los datos fiscales y los importes, detecta duplicados y guarda el resultado en una base de datos. Separa automáticamente las facturas que necesitan una revisión humana y genera un informe Excel. Todo se puede seguir desde un **panel web**.

> 🛠️ Proyecto personal de **automatización de procesos (RPA / hiperautomatización)**.

---

## Qué hace

```
 datos/entrada/*.pdf
        │
        ▼
 1. Texto ─────── PDF con texto → PyMuPDF  ·  PDF escaneado → OCR (Tesseract)
        │
        ▼
 2. Campos ────── nº de factura, fecha, emisor, NIF/CIF, base, IVA, total
        │         (varios formatos de proveedor, importes y fechas en español)
        ▼
 3. Validación ── NIF/NIE/CIF con dígito de control · base × IVA = cuota · base + IVA = total
        │         fecha no futura · tipo de IVA habitual · campos obligatorios · duplicados
        ▼
 4. Registro ──── SQLite
        │
        ├── válida ─────────► datos/procesadas/AAAA-MM/
        └── con incidencias ► datos/revision/  (+ nota .motivo.txt con el porqué)
                                        │
                                        ▼
                     informe Excel · panel web con indicadores y gráficos
```

**Validaciones**

| Control | Ejemplo de incidencia |
|---------|-----------------------|
| NIF/NIE/CIF con su algoritmo de dígito de control | `El NIF/CIF del emisor 'B86452130' no es válido` |
| Cuota de IVA coherente con la base y el tipo | `La cuota de IVA (10.00 €) no corresponde al 21% de la base (21.00 €)` |
| Total = base + IVA (con tolerancia de redondeo) | `El total (2500.00 €) no es la suma de base (1986.80 €) e IVA (417.23 €)` |
| Duplicados por contenido (SHA-256) o por emisor + número | `Factura duplicada: ya se registró en '01_suministros_correcta.pdf'` |
| Campos obligatorios, fecha no futura, tipo de IVA (0, 4, 10 o 21 %) | `Falta el campo obligatorio: número de factura` |

## Puesta en marcha

Requiere **Python 3.11 o superior**.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  ·  source .venv/bin/activate en Linux/macOS
pip install -r requirements.txt
```

**Probarlo con las facturas de ejemplo:**

```bash
python -m facturas ejemplos       # copia 9 facturas de prueba a datos/entrada
python -m facturas procesar       # las procesa
python -m facturas informe        # genera informes/facturas.xlsx
streamlit run panel.py            # panel web en http://localhost:8501
```

```
✔ 01_suministros_correcta.pdf → 2026-11 (F-2026-0412, 2404.03 €)
✔ 02_papeleria_correcta.pdf → 2026-10 (2026/118, 453.75 €)
✖ 05_error_total_mal_sumado.pdf → revisión: El total (2500.00 €) no es la suma de base (1986.80 €) e IVA (417.23 €)
✖ 07_duplicada.pdf → revisión: Factura duplicada: ya se registró en '01_suministros_correcta.pdf'
...
9 factura(s) procesada(s): 4 válida(s), 5 a revisión
```

**Modo automático:** `python -m facturas vigilar` revisa la carpeta de entrada cada pocos segundos y procesa cada PDF que llega. Antes de leerlo espera a que el fichero termine de copiarse.

**OCR para facturas escaneadas (opcional):** instala [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) con el idioma español. Sin él, los PDF escaneados no se pierden: van a revisión indicando el motivo.

## Panel web

`streamlit run panel.py` abre un panel que permite:

- subir facturas y procesarlas;
- ver indicadores: procesadas, válidas, en revisión e importe total;
- consultar las incidencias de cada factura;
- ver gráficos por proveedor y por mes;
- descargar el informe Excel.

Solo es accesible desde el propio equipo.

## Estructura

```
facturas/
├── extraccion.py   # texto del PDF y OCR
├── campos.py       # extracción de campos con expresiones regulares
├── validacion.py   # NIF/NIE/CIF, importes, fechas, obligatorios
├── almacen.py      # SQLite y detección de duplicados
├── informe.py      # Excel: válidas, en revisión, resumen por proveedor
├── flujo.py        # orquestación, movimiento de ficheros y vigilancia
└── __main__.py     # línea de comandos
panel.py            # panel web (Streamlit)
ejemplos/           # generador de facturas ficticias de tres formatos
tests/              # pytest
```

## Tests

```bash
python -m pytest
```

Hay **44 tests**: validación de NIF/NIE/CIF, cálculo de importes, extracción de los tres formatos de factura y el flujo completo sobre las facturas de ejemplo (clasificación, movimiento de ficheros, duplicados e informe). Se ejecutan en cada *push* con **GitHub Actions**.

Las facturas de ejemplo son **ficticias**: empresas y NIF inventados, con dígitos de control calculados para que sean válidos, salvo en el caso que prueba un CIF incorrecto.

## En VS Code

Al abrir la carpeta, VS Code usa el entorno `.venv` y detecta los tests (pestaña *Testing*). En *Run and Debug* hay configuraciones listas para el panel web, procesar, vigilar y cargar los ejemplos.
