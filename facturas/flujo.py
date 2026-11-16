"""Flujo completo de procesamiento de una factura y de una carpeta de entrada.

    entrada/  ──►  texto (PDF u OCR)  ──►  campos  ──►  validación + duplicados  ──►  SQLite
                                                                │
                              procesadas/AAAA-MM/  ◄── válida ──┴── con incidencias ──►  revision/
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .almacen import Almacen
from .campos import extraer_campos
from .extraccion import SinTexto, extraer_texto
from .modelo import Estado, Factura, Resultado
from .validacion import validar

log = logging.getLogger("facturas")


@dataclass
class Rutas:
    """Carpetas de trabajo del bot (por defecto, dentro de datos/)."""
    base: Path

    @property
    def entrada(self) -> Path:
        return self.base / "entrada"

    @property
    def procesadas(self) -> Path:
        return self.base / "procesadas"

    @property
    def revision(self) -> Path:
        return self.base / "revision"

    @property
    def bd(self) -> Path:
        return self.base / "facturas.db"

    def crear(self) -> None:
        for p in (self.entrada, self.procesadas, self.revision):
            p.mkdir(parents=True, exist_ok=True)


def huella(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def analizar(ruta: Path, almacen: Almacen) -> Resultado:
    """Extrae, valida y comprueba duplicados de un PDF (no mueve ni guarda nada)."""
    h = huella(ruta)
    try:
        texto, origen = extraer_texto(str(ruta))
    except SinTexto as e:
        return Resultado(ruta.name, Factura(), Estado.REVISION, [str(e)], "ninguno", h)
    except Exception as e:  # PDF dañado o que no es un PDF
        return Resultado(ruta.name, Factura(), Estado.REVISION, [f"No se pudo leer el PDF: {e}"], "ninguno", h)

    factura = extraer_campos(texto)
    incidencias = validar(factura)

    previo = almacen.duplicado_de(h, factura.nif_emisor, factura.numero)
    if previo:
        incidencias.append(f"Factura duplicada: ya se registró en '{previo}'")

    estado = Estado.VALIDA if not incidencias else Estado.REVISION
    return Resultado(ruta.name, factura, estado, incidencias, origen, h)


def _destino_libre(carpeta: Path, nombre: str) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre
    n = 1
    while destino.exists():
        destino = carpeta / f"{Path(nombre).stem}_{n}{Path(nombre).suffix}"
        n += 1
    return destino


def procesar_fichero(ruta: Path, rutas: Rutas, almacen: Almacen) -> Resultado:
    r = analizar(ruta, almacen)
    if r.estado == Estado.VALIDA:
        mes = r.factura.fecha.strftime("%Y-%m") if r.factura.fecha else "sin-fecha"
        destino = _destino_libre(rutas.procesadas / mes, ruta.name)
    else:
        destino = _destino_libre(rutas.revision, ruta.name)
        # Nota junto al PDF con los motivos, para quien lo revise
        destino.with_suffix(".motivo.txt").write_text(
            "Motivos de revisión:\n" + "\n".join(f"- {i}" for i in r.incidencias) + "\n", encoding="utf-8")
    shutil.move(str(ruta), destino)
    r.fichero = destino.name
    almacen.guardar(r)

    if r.estado == Estado.VALIDA:
        log.info("[OK]       %s -> %s (%s, %s €)%s", ruta.name, destino.parent.name, r.factura.numero, r.factura.total,
                 "  [leída con OCR]" if r.origen_texto == "ocr" else "")
    else:
        log.warning("[REVISIÓN] %s: %s", ruta.name, "; ".join(r.incidencias))
    return r


def procesar_carpeta(rutas: Rutas) -> list[Resultado]:
    rutas.crear()
    resultados = []
    with Almacen(rutas.bd) as almacen:
        # Un solo recorrido con la extensión en minúsculas: en Windows "*.pdf" y "*.PDF" coinciden
        for pdf in sorted(p for p in rutas.entrada.iterdir() if p.suffix.lower() == ".pdf"):
            resultados.append(procesar_fichero(pdf, rutas, almacen))
    return resultados


def vigilar(rutas: Rutas, intervalo: float = 5.0, espera_estable: float = 1.0) -> None:
    """Revisa la carpeta de entrada cada `intervalo` segundos y procesa los PDF nuevos.

    Antes de procesar un fichero espera a que su tamaño no cambie, para no leer
    un PDF que todavía se está copiando.
    """
    rutas.crear()
    log.info("Vigilando %s (Ctrl+C para parar)", rutas.entrada)
    try:
        while True:
            pendientes = [p for p in rutas.entrada.iterdir() if p.suffix.lower() == ".pdf"]
            if pendientes:
                tamanos = {p: p.stat().st_size for p in pendientes}
                time.sleep(espera_estable)
                estables = [p for p in pendientes if p.exists() and p.stat().st_size == tamanos[p]]
                with Almacen(rutas.bd) as almacen:
                    for p in sorted(estables):
                        procesar_fichero(p, rutas, almacen)
            time.sleep(intervalo)
    except KeyboardInterrupt:
        log.info("Vigilancia detenida")
