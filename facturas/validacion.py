"""Validaciones de negocio: NIF/NIE/CIF, coherencia de importes, fechas y campos obligatorios."""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from .modelo import Factura

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
LETRAS_CONTROL_CIF = "JABCDEFGHI"
TIPOS_IVA_VALIDOS = {Decimal("0"), Decimal("4"), Decimal("10"), Decimal("21")}
TOLERANCIA = Decimal("0.02")   # céntimos de redondeo admitidos


# ---------------------------------------------------------------------------
# Identificadores fiscales
# ---------------------------------------------------------------------------

def normalizar_nif(valor: str) -> str:
    return re.sub(r"[\s.\-]", "", valor).upper()


def nif_valido(valor: str | None) -> bool:
    """DNI (8 dígitos + letra), NIE (X/Y/Z + 7 dígitos + letra) o CIF (letra + 7 dígitos + control)."""
    if not valor:
        return False
    v = normalizar_nif(valor)

    if re.fullmatch(r"\d{8}[A-Z]", v):                      # DNI
        return LETRAS_DNI[int(v[:8]) % 23] == v[8]

    if re.fullmatch(r"[XYZ]\d{7}[A-Z]", v):                 # NIE
        numero = str("XYZ".index(v[0])) + v[1:8]
        return LETRAS_DNI[int(numero) % 23] == v[8]

    if re.fullmatch(r"[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]", v):  # CIF
        d = digito_control_cif(v[1:8])
        letra, numero = LETRAS_CONTROL_CIF[d], str(d)
        # Según el tipo de entidad, el control es una letra, un número o cualquiera de los dos
        if v[0] in "PQRSNW":
            return v[8] == letra
        if v[0] in "ABEH":
            return v[8] == numero
        return v[8] in (letra, numero)

    return False


def digito_control_cif(digitos: str) -> int:
    """Dígito de control (0-9) de un CIF a partir de sus 7 dígitos centrales."""
    pares = sum(int(digitos[i]) for i in (1, 3, 5))
    impares = 0
    for i in (0, 2, 4, 6):
        doble = int(digitos[i]) * 2
        impares += doble // 10 + doble % 10
    return (10 - (pares + impares) % 10) % 10


# ---------------------------------------------------------------------------
# Factura completa
# ---------------------------------------------------------------------------

def validar(f: Factura, hoy: date | None = None) -> list[str]:
    """Devuelve la lista de incidencias (vacía si la factura es correcta)."""
    hoy = hoy or date.today()
    inc: list[str] = []

    obligatorios = {
        "número de factura": f.numero, "fecha": f.fecha, "NIF del emisor": f.nif_emisor,
        "base imponible": f.base_imponible, "total": f.total,
    }
    for nombre, valor in obligatorios.items():
        if valor is None:
            inc.append(f"Falta el campo obligatorio: {nombre}")

    if f.nif_emisor and not nif_valido(f.nif_emisor):
        inc.append(f"El NIF/CIF del emisor '{f.nif_emisor}' no es válido (dígito de control incorrecto)")
    if f.nif_cliente and not nif_valido(f.nif_cliente):
        inc.append(f"El NIF/CIF del cliente '{f.nif_cliente}' no es válido")

    if f.fecha and f.fecha > hoy:
        inc.append(f"La fecha de la factura ({f.fecha:%d/%m/%Y}) es posterior a hoy")

    if f.tipo_iva is not None and f.tipo_iva not in TIPOS_IVA_VALIDOS:
        inc.append(f"Tipo de IVA no habitual en España: {f.tipo_iva}%")

    if f.base_imponible is not None and f.tipo_iva is not None and f.cuota_iva is not None:
        esperada = (f.base_imponible * f.tipo_iva / 100).quantize(Decimal("0.01"))
        if abs(esperada - f.cuota_iva) > TOLERANCIA:
            inc.append(f"La cuota de IVA ({f.cuota_iva} €) no corresponde al {f.tipo_iva}% "
                       f"de la base ({esperada} €)")

    if f.base_imponible is not None and f.total is not None:
        cuota = f.cuota_iva if f.cuota_iva is not None else Decimal("0")
        if abs(f.base_imponible + cuota - f.total) > TOLERANCIA:
            inc.append(f"El total ({f.total} €) no es la suma de base ({f.base_imponible} €) "
                       f"e IVA ({cuota} €)")

    return inc
