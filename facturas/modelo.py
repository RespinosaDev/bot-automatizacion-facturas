"""Modelo de datos de una factura y de su resultado de validación."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class Estado(str, Enum):
    VALIDA = "valida"          # todos los controles superados
    REVISION = "revision"      # necesita que una persona la revise


@dataclass
class Factura:
    """Campos extraídos de una factura. Los que no se encuentran quedan a None."""
    numero: str | None = None
    fecha: date | None = None
    emisor: str | None = None
    nif_emisor: str | None = None
    nif_cliente: str | None = None
    base_imponible: Decimal | None = None
    tipo_iva: Decimal | None = None      # porcentaje: 21, 10, 4 o 0
    cuota_iva: Decimal | None = None
    total: Decimal | None = None


@dataclass
class Resultado:
    """Resultado de procesar un fichero."""
    fichero: str
    factura: Factura
    estado: Estado
    incidencias: list[str] = field(default_factory=list)
    origen_texto: str = "pdf"             # "pdf" (texto nativo) u "ocr"
    huella: str = ""                      # SHA-256 del fichero, para detectar duplicados exactos
