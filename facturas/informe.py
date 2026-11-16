"""Informe en Excel: facturas válidas, facturas a revisar y resumen por proveedor."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

AZUL = "1D3557"
FORMATO_EUROS = '#,##0.00 "€"'
CABECERA = Font(bold=True, color="FFFFFF")
RELLENO = PatternFill("solid", fgColor=AZUL)


def _num(x) -> float | None:
    return None if x is None else float(Decimal(x))


def _fecha(x):
    return None if not x else date.fromisoformat(x)


def _hoja(ws, cabeceras, filas, columnas_euro=(), columnas_fecha=()):
    ws.append(cabeceras)
    for c in ws[1]:
        c.font, c.fill = CABECERA, RELLENO
        c.alignment = Alignment(vertical="center")
    for fila in filas:
        ws.append(fila)
    for col in columnas_euro:
        for celda in ws[get_column_letter(col)][1:]:
            celda.number_format = FORMATO_EUROS
    for col in columnas_fecha:
        for celda in ws[get_column_letter(col)][1:]:
            celda.number_format = "DD/MM/YYYY"
    for i, cab in enumerate(cabeceras, start=1):
        ancho = max([len(str(cab))] + [len(str(f[i - 1])) for f in filas if f[i - 1] is not None])
        ws.column_dimensions[get_column_letter(i)].width = min(ancho + 3, 70)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def generar_informe(facturas: list[dict], salida: str | Path) -> Path:
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    validas = [f for f in facturas if f["estado"] == "valida"]
    revision = [f for f in facturas if f["estado"] != "valida"]

    ws = wb.active
    ws.title = "Facturas válidas"
    _hoja(ws, ["Nº factura", "Fecha", "Emisor", "NIF emisor", "Base", "IVA %", "Cuota IVA", "Total", "Fichero"],
          [[f["numero"], _fecha(f["fecha"]), f["emisor"], f["nif_emisor"], _num(f["base"]), _num(f["tipo_iva"]),
            _num(f["cuota_iva"]), _num(f["total"]), f["fichero"]] for f in validas],
          columnas_euro=(5, 7, 8), columnas_fecha=(2,))

    ws = wb.create_sheet("En revisión")
    _hoja(ws, ["Fichero", "Nº factura", "Emisor", "Total", "Motivo"],
          [[f["fichero"], f["numero"], f["emisor"], _num(f["total"]), " · ".join(f["incidencias"])] for f in revision],
          columnas_euro=(4,))

    por_proveedor = defaultdict(lambda: [None, 0, Decimal(0), Decimal(0), Decimal(0)])
    for f in validas:
        p = por_proveedor[f["nif_emisor"]]
        # Mejor el nombre tal cual que en mayúsculas, si alguna factura lo trae así
        if p[0] is None or (p[0].isupper() and f["emisor"] and not f["emisor"].isupper()):
            p[0] = f["emisor"]
        p[1] += 1
        p[2] += Decimal(f["base"])
        p[3] += Decimal(f["cuota_iva"] or 0)
        p[4] += Decimal(f["total"])
    filas = sorted(([nombre, nif, n, float(b), float(i), float(t)]
                    for nif, (nombre, n, b, i, t) in por_proveedor.items()), key=lambda x: -x[5])
    ws = wb.create_sheet("Resumen por proveedor")
    _hoja(ws, ["Proveedor", "NIF", "Nº facturas", "Base", "IVA", "Total"], filas, columnas_euro=(4, 5, 6))
    if filas:
        # Las sumas se hacen con Decimal para no arrastrar errores de coma flotante
        totales = [sum((v[k] for v in por_proveedor.values()), Decimal(0)) for k in (2, 3, 4)]
        ws.append(["TOTAL", None, sum(f[2] for f in filas)] + [float(t) for t in totales])
        for c in ws[ws.max_row]:
            c.font = Font(bold=True)
        for col in (4, 5, 6):
            ws.cell(ws.max_row, col).number_format = FORMATO_EUROS

    wb.save(salida)
    return salida
