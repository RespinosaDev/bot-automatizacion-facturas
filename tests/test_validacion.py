from datetime import date, timedelta
from decimal import Decimal

import pytest

from facturas.modelo import Factura
from facturas.validacion import nif_valido, validar


@pytest.mark.parametrize("nif", ["12345678Z", "00000000T", "X1234567L", "Y1234567X", "B86452133", "A28731040",
                                 "b-86452133", "Q2826000H"])
def test_nif_validos(nif):
    assert nif_valido(nif)


@pytest.mark.parametrize("nif", ["12345678A", "X1234567A", "B86452130", "A2873104X", "Q2826000A", "123", "", None,
                                 "Z12345678"])
def test_nif_invalidos(nif):
    assert not nif_valido(nif)


def factura_correcta(**cambios):
    f = Factura(numero="F-1", fecha=date(2026, 11, 3), emisor="Ejemplo S.L.", nif_emisor="B86452133",
                nif_cliente="B73512063", base_imponible=Decimal("100.00"), tipo_iva=Decimal("21"),
                cuota_iva=Decimal("21.00"), total=Decimal("121.00"))
    for k, v in cambios.items():
        setattr(f, k, v)
    return f


def test_factura_correcta_no_tiene_incidencias():
    assert validar(factura_correcta(), hoy=date(2026, 11, 16)) == []


def test_total_que_no_cuadra():
    inc = validar(factura_correcta(total=Decimal("130.00")), hoy=date(2026, 11, 16))
    assert len(inc) == 1 and "no es la suma" in inc[0]


def test_cuota_de_iva_incorrecta():
    inc = validar(factura_correcta(cuota_iva=Decimal("10.00"), total=Decimal("110.00")), hoy=date(2026, 11, 16))
    assert any("no corresponde al 21%" in i for i in inc)


def test_se_toleran_los_centimos_de_redondeo():
    assert validar(factura_correcta(total=Decimal("121.01")), hoy=date(2026, 11, 16)) == []


def test_fecha_futura():
    inc = validar(factura_correcta(fecha=date(2026, 11, 16) + timedelta(days=3)), hoy=date(2026, 11, 16))
    assert any("posterior a hoy" in i for i in inc)


def test_campos_obligatorios():
    inc = validar(Factura(), hoy=date(2026, 11, 16))
    assert len(inc) == 5


def test_tipo_de_iva_no_habitual():
    inc = validar(factura_correcta(tipo_iva=Decimal("16"), cuota_iva=Decimal("16.00"), total=Decimal("116.00")),
                  hoy=date(2026, 11, 16))
    assert inc == ["Tipo de IVA no habitual en España: 16%"]
