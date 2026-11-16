"""Obtención del texto de un PDF: texto nativo o, si es un escaneo, OCR con Tesseract."""
from __future__ import annotations

import shutil

import pymupdf

MIN_CARACTERES = 40   # por debajo de esto se considera que el PDF es una imagen escaneada


class SinTexto(Exception):
    """El PDF no tiene texto y no hay OCR disponible para leerlo."""


def ocr_disponible() -> bool:
    return shutil.which("tesseract") is not None


def extraer_texto(ruta: str) -> tuple[str, str]:
    """Devuelve (texto, origen), donde origen es "pdf" u "ocr"."""
    with pymupdf.open(ruta) as doc:
        texto = "\n".join(pagina.get_text("text", sort=True) for pagina in doc)
        if len(texto.strip()) >= MIN_CARACTERES:
            return texto, "pdf"

        if not ocr_disponible():
            raise SinTexto("El PDF es una imagen escaneada y no hay OCR instalado (Tesseract)")

        partes = []
        for pagina in doc:
            tp = pagina.get_textpage_ocr(language="spa", dpi=300, full=True)
            partes.append(pagina.get_text("text", textpage=tp, sort=True))
        return "\n".join(partes), "ocr"
