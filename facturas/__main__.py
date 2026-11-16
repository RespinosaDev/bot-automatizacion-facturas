"""Línea de comandos del bot.

    python -m facturas procesar            procesa los PDF de datos/entrada
    python -m facturas vigilar             vigila datos/entrada y procesa lo que llegue
    python -m facturas informe             genera informes/facturas.xlsx
    python -m facturas ejemplos            copia facturas de ejemplo a datos/entrada
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

from .almacen import Almacen
from .extraccion import ocr_disponible
from .flujo import Rutas, procesar_carpeta, vigilar
from .informe import generar_informe

RAIZ = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m facturas", description="Bot de procesamiento de facturas en PDF")
    p.add_argument("--datos", default=str(RAIZ / "datos"), help="carpeta de trabajo (por defecto: datos/)")
    sub = p.add_subparsers(dest="orden", required=True)
    sub.add_parser("procesar", help="procesa los PDF de la carpeta de entrada")
    v = sub.add_parser("vigilar", help="vigila la carpeta de entrada")
    v.add_argument("--intervalo", type=float, default=5.0, help="segundos entre revisiones")
    i = sub.add_parser("informe", help="genera el informe Excel")
    i.add_argument("--salida", default=str(RAIZ / "informes" / "facturas.xlsx"))
    sub.add_parser("ejemplos", help="copia las facturas de ejemplo a la carpeta de entrada")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    rutas = Rutas(Path(args.datos))

    if args.orden == "procesar":
        if not ocr_disponible():
            logging.info("OCR no disponible: los PDF escaneados irán a revisión (instala Tesseract para leerlos)")
        res = procesar_carpeta(rutas)
        validas = sum(r.estado.value == "valida" for r in res)
        print(f"\n{len(res)} factura(s) procesada(s): {validas} válida(s), {len(res) - validas} a revisión")
    elif args.orden == "vigilar":
        vigilar(rutas, args.intervalo)
    elif args.orden == "informe":
        with Almacen(rutas.bd) as a:
            salida = generar_informe(a.todas(), args.salida)
        print(f"Informe generado: {salida}")
    elif args.orden == "ejemplos":
        origen = RAIZ / "ejemplos" / "facturas"
        if not origen.exists():
            from ejemplos.generar_facturas import generar
            generar(origen)
        rutas.crear()
        for pdf in sorted(origen.glob("*.pdf")):
            shutil.copy(pdf, rutas.entrada / pdf.name)
        print(f"Copiadas las facturas de ejemplo a {rutas.entrada}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
