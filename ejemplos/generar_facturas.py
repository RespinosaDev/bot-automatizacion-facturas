"""Genera facturas PDF ficticias para probar el bot.

Tres proveedores con formatos distintos y varios casos con errores intencionados.
Todos los datos son inventados; los CIF tienen un dígito de control calculado (válido)
salvo en el caso que prueba un CIF incorrecto.

Uso:  python ejemplos/generar_facturas.py [carpeta_destino]
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from facturas.validacion import LETRAS_CONTROL_CIF, digito_control_cif  # noqa: E402

AZUL = (0.11, 0.21, 0.34)
FUENTES = Path(__file__).resolve().parent / "fuentes"
REGULAR = str(FUENTES / "Inter-Regular.ttf")   # Inter (licencia OFL): incluye el símbolo €
NEGRITA = str(FUENTES / "Inter-Bold.ttf")


def texto(page, pos, cadena, fontsize=10, negrita=False, color=(0, 0, 0)):
    page.insert_text(pos, cadena, fontsize=fontsize, color=color,
                     fontname="interb" if negrita else "inter", fontfile=NEGRITA if negrita else REGULAR)
GRIS = (0.35, 0.35, 0.35)


def cif(letra: str, digitos: str) -> str:
    d = digito_control_cif(digitos)
    control = LETRAS_CONTROL_CIF[d] if letra in "PQRSNW" else str(d)
    return f"{letra}{digitos}{control}"


def euros(x: Decimal) -> str:
    entero, dec = f"{x:.2f}".split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{entero},{dec} €"


PROVEEDORES = {
    "suministros": ("Suministros Informáticos Madrid S.L.", cif("B", "8645213"),
                    "C/ Alcalá 120, 28009 Madrid"),
    "papeleria": ("Papelería Central S.A.", cif("A", "2873104"), "Av. de la Constitución 8, 41004 Sevilla"),
    "consultoria": ("Consultoría Norte S.L.", cif("B", "4810397"), "Gran Vía 45, 48011 Bilbao"),
}
CLIENTE = ("Talleres Ejemplo S.L.", cif("B", "7351206"), "C/ Mayor 3, 28013 Madrid")


def lineas_totales(lineas, tipo):
    base = sum((Decimal(c) * Decimal(p) for _, c, p in lineas), Decimal("0")).quantize(Decimal("0.01"))
    cuota = (base * Decimal(tipo) / 100).quantize(Decimal("0.01"))
    return base, cuota, base + cuota


def tabla(page, y, lineas, cabecera=("Descripción", "Cant.", "Precio", "Importe")):
    xs = (50, 340, 400, 480)
    for x, t in zip(xs, cabecera):
        texto(page, (x, y), t, fontsize=9.5, negrita=True, color=AZUL)
    page.draw_line((50, y + 5), (545, y + 5), color=AZUL, width=0.6)
    y += 20
    for desc, cant, precio in lineas:
        importe = Decimal(cant) * Decimal(precio)
        for x, t in zip(xs, (desc, str(cant), euros(Decimal(precio)), euros(importe))):
            texto(page, (x, y), t, fontsize=9.5)
        y += 16
    page.draw_line((50, y - 6), (545, y - 6), color=GRIS, width=0.3)
    return y + 10


def formato_a(doc, numero, fecha, prov, lineas, tipo=21, total_forzado=None, cif_emisor=None):
    """Formato clásico: emisor arriba a la izquierda, FACTURA a la derecha, totales abajo."""
    nombre, nif, direccion = PROVEEDORES[prov]
    page = doc.new_page()
    texto(page, (50, 60), nombre, fontsize=15, negrita=True, color=AZUL)
    texto(page, (50, 78), f"CIF: {cif_emisor or nif}", fontsize=9.5)
    texto(page, (50, 92), direccion, fontsize=9.5, color=GRIS)
    texto(page, (420, 60), "FACTURA", fontsize=20, negrita=True, color=AZUL)
    if numero:
        texto(page, (400, 82), f"Nº Factura: {numero}", fontsize=10)
    texto(page, (400, 96), f"Fecha: {fecha}", fontsize=10)
    texto(page, (50, 135), "Cliente:", fontsize=10, negrita=True, color=AZUL)
    texto(page, (50, 150), f"{CLIENTE[0]}   NIF: {CLIENTE[1]}", fontsize=9.5)
    texto(page, (50, 164), CLIENTE[2], fontsize=9.5, color=GRIS)
    y = tabla(page, 200, lineas)
    base, cuota, total = lineas_totales(lineas, tipo)
    total = total_forzado or total
    for etiqueta, valor in ((f"Base imponible: {euros(base)}", 0), (f"IVA ({tipo}%): {euros(cuota)}", 1),
                            (f"TOTAL: {euros(total)}", 2)):
        texto(page, (360, y + 18 * valor), etiqueta, fontsize=11 if valor == 2 else 10,
                         negrita=valor == 2, color=AZUL if valor == 2 else (0, 0, 0))
    texto(page, (50, 800), "Forma de pago: transferencia a 30 días.", fontsize=8.5, color=GRIS)


def formato_b(doc, numero, fecha_texto, prov, lineas, tipo=10):
    """Formato con bloques de proveedor y cliente lado a lado y fecha con el mes en letra."""
    nombre, nif, direccion = PROVEEDORES[prov]
    page = doc.new_page()
    texto(page, (50, 55), f"Factura número {numero}", fontsize=16, negrita=True, color=AZUL)
    texto(page, (50, 75), f"Fecha de emisión: {fecha_texto}", fontsize=10)
    texto(page, (50, 115), f"Proveedor: {nombre}", fontsize=10)
    texto(page, (50, 130), f"CIF: {nif}", fontsize=10)
    texto(page, (50, 145), direccion, fontsize=9.5, color=GRIS)
    texto(page, (50, 180), f"Facturar a: {CLIENTE[0]}", fontsize=10)
    texto(page, (50, 195), f"NIF: {CLIENTE[1]}", fontsize=10)
    y = tabla(page, 235, lineas, ("Concepto", "Uds.", "P. unitario", "Importe"))
    base, cuota, total = lineas_totales(lineas, tipo)
    texto(page, (330, y), f"Base imponible: {euros(base)}", fontsize=10)
    texto(page, (330, y + 16), f"Cuota IVA {tipo}%: {euros(cuota)}", fontsize=10)
    texto(page, (330, y + 34), f"Total a pagar: {euros(total)}", fontsize=12, negrita=True, color=AZUL)


def formato_c(doc, numero, fecha, prov, lineas, tipo=4):
    """Formato bilingüe (español/inglés) con 'Invoice No.' y 'Subtotal'."""
    nombre, nif, direccion = PROVEEDORES[prov]
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(0, 0, 595, 90), color=None, fill=AZUL)
    texto(page, (50, 45), nombre.upper(), fontsize=14, negrita=True, color=(1, 1, 1))
    texto(page, (50, 65), f"VAT/CIF {nif} · {direccion}", fontsize=8.5, color=(1, 1, 1))
    texto(page, (50, 125), "INVOICE / FACTURA", fontsize=13, negrita=True, color=AZUL)
    texto(page, (50, 145), f"Invoice No.: {numero}", fontsize=10)
    texto(page, (50, 160), f"Fecha / Date: {fecha}", fontsize=10)
    texto(page, (330, 125), "Bill to:", fontsize=10, negrita=True, color=AZUL)
    texto(page, (330, 140), CLIENTE[0], fontsize=10)
    texto(page, (330, 155), f"NIF {CLIENTE[1]}", fontsize=10)
    y = tabla(page, 200, lineas, ("Item", "Qty", "Price", "Amount"))
    base, cuota, total = lineas_totales(lineas, tipo)
    texto(page, (360, y), f"Subtotal: {euros(base)}", fontsize=10)
    texto(page, (360, y + 16), f"IVA {tipo}%: {euros(cuota)}", fontsize=10)
    texto(page, (360, y + 34), f"Total (EUR): {euros(total)}", fontsize=12, negrita=True, color=AZUL)


def escaneada(origen: Path, destino: Path):
    """Convierte un PDF en una imagen sin texto, como si viniera de un escáner."""
    with pymupdf.open(origen) as src:
        pix = src[0].get_pixmap(dpi=150, colorspace=pymupdf.csGRAY)
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(page.rect, pixmap=pix)
    doc.save(destino)


def generar(carpeta: Path) -> list[Path]:
    carpeta.mkdir(parents=True, exist_ok=True)
    ordenadores = [("Portátil 14\" i5 16 GB", 2, "689.00"), ("Monitor 27\" QHD", 2, "219.90"),
                   ("Docking station USB-C", 2, "84.50")]
    papel = [("Paquete folios A4 (500 h.)", 40, "4.35"), ("Tóner láser negro", 3, "62.00"),
             ("Archivadores de palanca", 25, "2.10")]
    libros = [("Manual de normativa fiscal 2026", 3, "38.00"), ("Suscripción revista técnica", 1, "120.00")]
    consultoria = [("Auditoría de procesos (horas)", 12, "65.00"), ("Informe de recomendaciones", 1, "450.00")]

    casos = {
        "01_suministros_correcta.pdf": lambda d: formato_a(d, "F-2026-0412", "03/11/2026", "suministros", ordenadores),
        "02_papeleria_correcta.pdf": lambda d: formato_b(d, "2026/118", "5 de octubre de 2026", "papeleria", papel),
        "03_consultoria_correcta.pdf": lambda d: formato_c(d, "INV-3391", "28.10.2026", "consultoria", libros),
        "04_consultoria_servicios.pdf": lambda d: formato_a(d, "F-2026-0533", "10/11/2026", "consultoria",
                                                           consultoria),
        "05_error_total_mal_sumado.pdf": lambda d: formato_a(d, "F-2026-0418", "07/11/2026", "suministros",
                                                            ordenadores, total_forzado=Decimal("2500.00")),
        "06_error_cif_invalido.pdf": lambda d: formato_a(d, "F-2026-0420", "08/11/2026", "suministros",
                                                        papel, cif_emisor="B86452130"),
        "07_duplicada.pdf": lambda d: formato_a(d, "F-2026-0412", "03/11/2026", "suministros", ordenadores),
        "08_error_sin_numero.pdf": lambda d: formato_a(d, None, "12/11/2026", "suministros", papel),
    }
    creados = []
    for nombre, dibujar in casos.items():
        doc = pymupdf.open()
        dibujar(doc)
        ruta = carpeta / nombre
        doc.save(ruta)
        creados.append(ruta)
    escaneada(carpeta / "02_papeleria_correcta.pdf", carpeta / "09_escaneada.pdf")
    creados.append(carpeta / "09_escaneada.pdf")
    return creados


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "facturas"
    for r in generar(destino):
        print("Creada", r)
