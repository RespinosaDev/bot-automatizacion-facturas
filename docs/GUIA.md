# Guía del bot de facturas

Cómo usarlo en el día a día, cómo funciona por dentro y cómo ampliarlo.

---

## 1. Uso diario

### Primera vez

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python ocr/descargar_idioma.py
```

### Procesar facturas

1. Deja los PDF en `datos/entrada/`.
2. Ejecuta `python -m facturas procesar`.
3. Mira el resultado:
   - `datos/procesadas/AAAA-MM/`: facturas correctas, ordenadas por mes.
   - `datos/revision/`: facturas con algún problema; junto a cada una, un `.motivo.txt` explica qué falla.
4. `python -m facturas informe` genera `informes/facturas.xlsx` con tres hojas: válidas, en revisión y resumen por proveedor.

### Modo automático

`python -m facturas vigilar` se queda en marcha y procesa cada PDF que aparezca en `datos/entrada/`; se para con Ctrl+C. Es el modo pensado para dejarlo funcionando, por ejemplo, con la carpeta donde un escáner o un programa de correo guarda las facturas.

### Panel web

`streamlit run panel.py` y abre http://localhost:8501. Desde ahí:
- subes PDF (barra lateral → *Guardar en la carpeta de entrada*) y pulsas **Procesar pendientes**;
- consultas indicadores, la tabla de válidas (con la columna *Lectura*: texto del PDF u OCR), las incidencias y los gráficos;
- descargas el Excel.

### Desde VS Code

- **Run and Debug** (Ctrl+Shift+D): *Panel web*, *Procesar*, *Vigilar* y *Cargar facturas de ejemplo*.
- **Testing** (icono del matraz): ejecuta los 46 tests o uno concreto.

### Empezar de cero

Borra `datos/facturas.db` y vacía `datos/procesadas/` y `datos/revision/`. `python -m facturas ejemplos` vuelve a cargar las 9 facturas de prueba.

---

## 2. Cómo funciona

```
PDF ─► extraccion.py ─► campos.py ─► validacion.py ─► almacen.py ─► flujo.py mueve el fichero
        texto u OCR       regex         reglas          SQLite        procesadas/ o revision/
```

| Módulo | Qué hace | Ideas clave |
|--------|----------|-------------|
| `extraccion.py` | Saca el texto del PDF | Si tiene menos de 40 caracteres, es una imagen escaneada y se aplica OCR con Tesseract al 300 ppp |
| `campos.py` | Encuentra cada dato en el texto | Varias expresiones regulares por campo, de la más específica a la más general; importes `1.234,56`; fechas `03/11/2026` o `5 de octubre de 2026`; el NIF del cliente es el que aparece tras "Cliente", "Facturar a" o "Bill to" |
| `validacion.py` | Comprueba que la factura es correcta | Dígito de control de DNI, NIE y CIF; base × IVA = cuota; base + cuota = total con 2 céntimos de margen; fecha no futura; tipos de IVA 0/4/10/21 |
| `almacen.py` | Guarda en SQLite | Duplicado si el contenido es idéntico (huella SHA-256) o si coinciden emisor y número |
| `informe.py` | Excel con openpyxl | Formato de euros y fechas, filtros y totales calculados con `Decimal` |
| `flujo.py` | Une todo | Una factura siempre termina en `procesadas/` o `revision/`, nunca se pierde; en modo vigilancia espera a que el fichero termine de copiarse |
| `panel.py` | Interfaz web con Streamlit | Lee la misma base de datos; solo es accesible desde el propio equipo |

**Por qué `Decimal` y no `float`:** con dinero, `float` acumula errores (0,1 + 0,2 = 0,30000000000000004). `Decimal` calcula exactamente con céntimos.

**Por qué las facturas de ejemplo son generadas:** no se pueden publicar facturas reales, porque contienen datos de empresas y personas. El generador crea facturas ficticias de tres formatos distintos, más casos con errores a propósito. Así cada regla tiene un caso que la demuestra.

### El OCR

- **Qué es:** el OCR (reconocimiento óptico de caracteres) convierte una imagen de texto en texto real. Una factura escaneada es una foto: sin OCR el programa solo ve píxeles.
- **Tesseract:** es el motor de OCR de código abierto más usado. Lo creó HP, después lo desarrolló Google y hoy lo mantiene la comunidad.
- **Cómo lo usa el bot:** PyMuPDF lleva el motor incorporado y solo necesita el modelo del idioma (`spa.traineddata`), que descarga `ocr/descargar_idioma.py`.
- **En este equipo:** además se instaló Tesseract con `winget install UB-Mannheim.TesseractOCR`. Así también está disponible para otros programas o desde la consola (`"C:\Program Files\Tesseract-OCR\tesseract.exe"`).

---

## 3. Cómo ampliarlo

- **Un proveedor con otro formato:** si algún campo no se reconoce, añade una expresión regular a la lista de ese campo en `campos.py` y un test en `tests/test_campos.py` con un texto de ejemplo.
- **Una regla nueva** (por ejemplo, "importe máximo por proveedor"): añádela en `validar()` de `validacion.py`, que devuelve la lista de incidencias, con su test.
- **Leer facturas del correo:** un módulo que descargue los adjuntos PDF de un buzón (IMAP, con la librería estándar `imaplib`) y los deje en `datos/entrada/`. El resto del flujo no cambia.
- **Llevarlo a un servidor:** un `Dockerfile` con Python y `tesseract-ocr-spa`, y el modo `vigilar` como proceso principal.

---

## 4. Problemas conocidos

- **La primera ejecución tarda o falla una vez con "Una directiva de Control de aplicaciones bloqueó este archivo":** es Smart App Control de Windows analizando las librerías nuevas (NumPy). La segunda vez funciona.
- **"no hay OCR disponible":** falta `spa.traineddata`. Ejecuta `python ocr/descargar_idioma.py`.
- **Una factura válida va a revisión por un campo que falta:** su formato usa una etiqueta que el bot no conoce. Mira su texto con:
  ```bash
  python -c "from facturas.extraccion import extraer_texto; print(extraer_texto('ruta.pdf')[0])"
  ```
  y añade la variante en `campos.py`.

---

## 5. Cómo explicarlo en una entrevista

> "Es un bot de automatización documental. Lee facturas en PDF, también escaneadas con OCR, extrae los datos fiscales y los valida con reglas de negocio reales. Por ejemplo, el dígito de control del CIF o que el total cuadre con la base y el IVA. Detecta duplicados, registra todo en una base de datos y separa automáticamente lo que necesita revisión humana, explicando el motivo. Lo complementa un panel web y un informe Excel, y está cubierto con tests que se ejecutan en GitHub Actions."

Preguntas que pueden hacerte:
- **¿Por qué expresiones regulares y no un modelo entrenado?** Para facturas con formato conocido son deterministas, rápidas y explicables. Lo que no se reconoce va a revisión en lugar de inventarse un dato.
- **¿Qué pasa si falla algo?** Ninguna factura se pierde: termina en `procesadas/` o en `revision/` con su motivo.
- **¿Cómo lo escalarías?** Lectura del correo, Docker, una base de datos de servidor (PostgreSQL) y colas para procesar en paralelo.
