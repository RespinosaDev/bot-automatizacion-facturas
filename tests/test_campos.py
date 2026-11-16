from datetime import date
from decimal import Decimal

import pytest

from facturas.campos import extraer_campos, importe
from facturas.extraccion import extraer_texto


@pytest.mark.parametrize("texto,esperado", [
    ("1.234,56", Decimal("1234.56")), ("1.234,56 €", Decimal("1234.56")), ("12,50", Decimal("12.50")),
    ("1234.56", Decimal("1234.56")), ("1.000.000,00", Decimal("1000000.00")), ("", None), ("abc", None),
])
def test_importes_en_formato_espanol(texto, esperado):
    assert importe(texto) == esperado


def test_texto_con_otras_etiquetas():
    texto = """ACME Herramientas S.L.
    CIF: B86452133
    Número de factura: A/2026/77
    Fecha de expedición: 2 de noviembre de 2026
    Datos del cliente: Talleres Ejemplo S.L.  NIF 12345678Z
    Subtotal: 50,00 €
    I.V.A. 21%: 10,50 €
    Total factura: 60,50 €"""
    f = extraer_campos(texto)
    assert f.numero == "A/2026/77"
    assert f.fecha == date(2026, 11, 2)
    assert f.emisor == "ACME Herramientas S.L."
    assert (f.nif_emisor, f.nif_cliente) == ("B86452133", "12345678Z")
    assert (f.base_imponible, f.tipo_iva, f.cuota_iva, f.total) == (Decimal("50.00"), 21, Decimal("10.50"),
                                                                   Decimal("60.50"))


@pytest.mark.parametrize("fichero,numero,fecha,nif,total", [
    ("01_suministros_correcta.pdf", "F-2026-0412", date(2026, 11, 3), "B86452133", Decimal("2404.03")),
    ("02_papeleria_correcta.pdf", "2026/118", date(2026, 10, 5), "A28731040", Decimal("453.75")),
    ("03_consultoria_correcta.pdf", "INV-3391", date(2026, 10, 28), "B48103972", Decimal("243.36")),
])
def test_los_tres_formatos_de_ejemplo(facturas_ejemplo, fichero, numero, fecha, nif, total):
    texto, origen = extraer_texto(str(facturas_ejemplo / fichero))
    f = extraer_campos(texto)
    assert origen == "pdf"
    assert (f.numero, f.fecha, f.nif_emisor, f.total) == (numero, fecha, nif, total)
    assert f.nif_cliente == "B73512063"
