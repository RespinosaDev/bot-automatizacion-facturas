"""Pruebas del OCR. Se omiten si no está disponible el modelo de español de Tesseract."""
import shutil
from datetime import date
from decimal import Decimal

import pytest

from facturas.campos import extraer_campos
from facturas.extraccion import extraer_texto, ocr_disponible
from facturas.flujo import Rutas, procesar_carpeta

pytestmark = pytest.mark.skipif(not ocr_disponible(), reason="OCR no disponible (falta spa.traineddata)")


def test_lee_una_factura_escaneada(facturas_ejemplo):
    texto, origen = extraer_texto(str(facturas_ejemplo / "09_escaneada.pdf"))
    assert origen == "ocr"
    f = extraer_campos(texto)
    assert (f.numero, f.fecha, f.nif_emisor, f.nif_cliente) == ("2026/131", date(2026, 11, 11), "A28731040",
                                                               "B73512063")
    assert (f.base_imponible, f.tipo_iva, f.cuota_iva, f.total) == (Decimal("227.30"), 21, Decimal("47.73"),
                                                                   Decimal("275.03"))


def test_la_escaneada_se_valida_como_las_demas(facturas_ejemplo, tmp_path):
    rutas = Rutas(tmp_path / "datos")
    rutas.crear()
    shutil.copy(facturas_ejemplo / "09_escaneada.pdf", rutas.entrada)
    (r,) = procesar_carpeta(rutas)
    assert r.estado.value == "valida", r.incidencias
    assert r.origen_texto == "ocr"
    assert (rutas.procesadas / "2026-11" / "09_escaneada.pdf").exists()
