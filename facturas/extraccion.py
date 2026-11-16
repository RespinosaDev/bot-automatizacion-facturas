"""Obtención del texto de un PDF: texto nativo o, si es un escaneo, OCR con Tesseract.

El OCR usa el motor de Tesseract que incluye PyMuPDF, que solo necesita el modelo del
idioma (spa.traineddata). Se busca, por este orden, en:

1. la carpeta indicada en la variable de entorno TESSDATA_PREFIX,
2. ocr/tessdata/ dentro del proyecto (lo descarga ocr/descargar_idioma.py),
3. la carpeta tessdata de una instalación de Tesseract (Windows, Linux o macOS).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pymupdf

MIN_CARACTERES = 40   # por debajo de esto se considera que el PDF es una imagen escaneada
IDIOMA = "spa"
DPI_OCR = 300

RAIZ = Path(__file__).resolve().parent.parent
CANDIDATAS = [
    RAIZ / "ocr" / "tessdata",
    Path(r"C:\Program Files\Tesseract-OCR\tessdata"),
    Path("/usr/share/tesseract-ocr/5/tessdata"),
    Path("/usr/share/tesseract-ocr/4.00/tessdata"),
    Path("/usr/local/share/tessdata"),
    Path("/opt/homebrew/share/tessdata"),
]


class SinTexto(Exception):
    """El PDF no tiene texto y no hay OCR disponible para leerlo."""


@lru_cache(maxsize=1)
def buscar_tessdata() -> str | None:
    """Carpeta con el modelo del idioma, o None si no hay ninguna."""
    carpetas = ([Path(os.environ["TESSDATA_PREFIX"])] if os.environ.get("TESSDATA_PREFIX") else []) + CANDIDATAS
    for carpeta in carpetas:
        if (carpeta / f"{IDIOMA}.traineddata").is_file():
            return str(carpeta)
    return None


def ocr_disponible() -> bool:
    return buscar_tessdata() is not None


def extraer_texto(ruta: str) -> tuple[str, str]:
    """Devuelve (texto, origen), donde origen es "pdf" u "ocr"."""
    with pymupdf.open(ruta) as doc:
        texto = "\n".join(pagina.get_text("text", sort=True) for pagina in doc)
        if len(texto.strip()) >= MIN_CARACTERES:
            return texto, "pdf"

        if not ocr_disponible():
            raise SinTexto("El PDF es una imagen escaneada y no hay OCR disponible "
                           "(falta el modelo de español: python ocr/descargar_idioma.py)")

        partes = []
        for pagina in doc:
            tp = pagina.get_textpage_ocr(language=IDIOMA, dpi=DPI_OCR, full=True, tessdata=buscar_tessdata())
            partes.append(pagina.get_text("text", textpage=tp, sort=True))
        return "\n".join(partes), "ocr"
