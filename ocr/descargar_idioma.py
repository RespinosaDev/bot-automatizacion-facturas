"""Descarga el modelo de idioma de Tesseract necesario para el OCR (español por defecto).

Los modelos se guardan en ocr/tessdata/ (no se suben al repositorio por su tamaño).

Uso:  python ocr/descargar_idioma.py [idioma ...]      p. ej.:  python ocr/descargar_idioma.py spa eng
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

# Modelos oficiales de Tesseract ("best": los más precisos)
URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main/{idioma}.traineddata"
DESTINO = Path(__file__).resolve().parent / "tessdata"


def descargar(idioma: str) -> Path:
    DESTINO.mkdir(parents=True, exist_ok=True)
    ruta = DESTINO / f"{idioma}.traineddata"
    if ruta.exists():
        print(f"{ruta.name} ya estaba descargado")
        return ruta
    print(f"Descargando {ruta.name}...")
    temporal = ruta.with_suffix(".parcial")
    urllib.request.urlretrieve(URL.format(idioma=idioma), temporal)
    temporal.replace(ruta)
    print(f"Guardado en {ruta} ({ruta.stat().st_size / 1e6:.1f} MB)")
    return ruta


if __name__ == "__main__":
    for idioma in sys.argv[1:] or ["spa"]:
        descargar(idioma)
