"""Extracción de los campos de una factura a partir de su texto.

Las facturas de distintos proveedores escriben lo mismo de formas diferentes
("Nº Factura", "Factura número", "Invoice No."), así que cada campo se busca con
varias expresiones regulares, de la más específica a la más general.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from .modelo import Factura
from .validacion import normalizar_nif

MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}

IMPORTE = r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})"
# Sin \b final: en los PDF el NIF aparece a veces pegado a la palabra siguiente ("B73512063Fecha")
NIF = r"(?<![A-Z0-9])([A-HJNP-SUVW]-?\d{7}[0-9A-J]|\d{8}-?[A-Z]|[XYZ]-?\d{7}-?[A-Z])(?![0-9])"
SOCIEDAD = re.compile(
    r"([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.,&' -]*?\b(?:S\.L\.U\.|S\.L\.|S\.A\.U\.|S\.A\.|SLU|SL|SA|S\.\s?Coop\.))"
    r"(?=\s|$)", re.IGNORECASE)
MARCAS_CLIENTE = r"(cliente|facturar\s+a|destinatario|datos\s+del\s+cliente|bill\s+to)"


def importe(texto: str | None) -> Decimal | None:
    """'1.234,56' -> Decimal('1234.56'); también admite '1234.56'."""
    if not texto:
        return None
    t = texto.strip().replace("€", "").strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return Decimal(t).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _buscar(patrones: list[str], texto: str, grupo: int = 1, ultimo: bool = False) -> str | None:
    for p in patrones:
        coincidencias = list(re.finditer(p, texto, re.IGNORECASE | re.MULTILINE))
        if coincidencias:
            m = coincidencias[-1] if ultimo else coincidencias[0]
            return m.group(grupo)
    return None


def _fecha(texto: str) -> date | None:
    m = re.search(r"fecha[^\n\d]{0,30}?(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", texto, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", texto)
    if m:
        d, mes, a = (int(x) for x in m.groups())
        if a < 100:
            a += 2000
        try:
            return date(a, mes, d)
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")\s+de\s+(\d{4})\b", texto, re.IGNORECASE)
    if m:
        try:
            return date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))
        except ValueError:
            return None
    return None


def _nifs(texto: str) -> tuple[str | None, str | None]:
    """NIF del emisor y del cliente. El del cliente es el que aparece tras su encabezado."""
    marca = re.search(MARCAS_CLIENTE, texto, re.IGNORECASE)
    antes, despues = (texto[:marca.start()], texto[marca.start():]) if marca else (texto, "")
    en_antes = [normalizar_nif(n) for n in re.findall(NIF, antes)]
    en_despues = [normalizar_nif(n) for n in re.findall(NIF, despues)]
    if marca:
        emisor = en_antes[0] if en_antes else None
        cliente = en_despues[0] if en_despues else None
        if emisor is None and len(en_despues) > 1:      # bloque del emisor tras el del cliente
            emisor = en_despues[1]
        return emisor, cliente
    todos = en_antes
    return (todos[0] if todos else None), (todos[1] if len(todos) > 1 else None)


def _emisor(texto: str) -> str | None:
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    marca = next((i for i, l in enumerate(lineas) if re.search(MARCAS_CLIENTE, l, re.IGNORECASE)), len(lineas))
    # Primero, el nombre de una sociedad (termina en S.L., S.A...), aunque comparta línea con otro texto
    for l in lineas[:marca]:
        l = re.sub(r"^(emisor|proveedor|raz[oó]n social)\s*:\s*", "", l, flags=re.IGNORECASE)
        m = SOCIEDAD.search(l)
        if m:
            return m.group(1).strip()
    for l in lineas[:marca]:
        if not re.search(r"factura|invoice|fecha|n[ºo°]", l, re.IGNORECASE) and re.search(r"[A-Za-z]{3}", l):
            return re.sub(r"^(emisor|proveedor|raz[oó]n social)\s*:\s*", "", l, flags=re.IGNORECASE)
    return None


def extraer_campos(texto: str) -> Factura:
    f = Factura()
    f.numero = _buscar([
        r"n[ºo°]\.?\s*(?:de\s+)?factura\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
        r"factura\s*(?:n[ºo°]\.?|n[uú]mero|num\.?)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
        r"n[uú]mero\s+de\s+factura\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
        r"invoice\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
    ], texto)
    f.fecha = _fecha(texto)
    f.emisor = _emisor(texto)
    f.nif_emisor, f.nif_cliente = _nifs(texto)
    f.base_imponible = importe(_buscar([
        r"base\s+imponible\s*:?\s*" + IMPORTE,
        r"subtotal\s*:?\s*" + IMPORTE,
    ], texto))

    m = re.search(r"I\.?V\.?A\.?\s*\(?\s*(\d{1,2}(?:[.,]\d+)?)\s*%\s*\)?\s*:?\s*" + IMPORTE + r"?", texto, re.IGNORECASE)
    if m:
        tipo = Decimal(m.group(1).replace(",", "."))
        f.tipo_iva = Decimal(int(tipo)) if tipo == tipo.to_integral_value() else tipo
        f.cuota_iva = importe(m.group(2))
    if f.cuota_iva is None:
        f.cuota_iva = importe(_buscar([r"cuota\s+(?:de\s+)?I\.?V\.?A\.?\s*:?\s*" + IMPORTE], texto))

    f.total = importe(_buscar([
        r"(?<!sub)total\s+(?:factura|a\s+pagar|\(eur\)|eur)\s*:?\s*" + IMPORTE,
        r"(?<!sub)total\s*:?\s*" + IMPORTE,
    ], texto, ultimo=True))
    return f
