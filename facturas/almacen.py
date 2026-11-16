"""Almacenamiento de las facturas procesadas en SQLite."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .modelo import Estado, Resultado

ESQUEMA = """
CREATE TABLE IF NOT EXISTS facturas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fichero       TEXT NOT NULL,
    huella        TEXT NOT NULL,
    numero        TEXT,
    fecha         TEXT,
    emisor        TEXT,
    nif_emisor    TEXT,
    nif_cliente   TEXT,
    base          TEXT,
    tipo_iva      TEXT,
    cuota_iva     TEXT,
    total         TEXT,
    estado        TEXT NOT NULL,
    origen_texto  TEXT NOT NULL,
    incidencias   TEXT NOT NULL,       -- lista JSON
    procesada_en  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_emisor_numero ON facturas (nif_emisor, numero);
CREATE INDEX IF NOT EXISTS idx_huella ON facturas (huella);
"""

COLUMNAS = ["id", "fichero", "numero", "fecha", "emisor", "nif_emisor", "nif_cliente", "base", "tipo_iva",
            "cuota_iva", "total", "estado", "origen_texto", "incidencias", "procesada_en"]


class Almacen:
    def __init__(self, ruta: str | Path):
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(ruta))
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)

    def cerrar(self) -> None:
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cerrar()

    # --- duplicados ---------------------------------------------------------

    def duplicado_de(self, huella: str, nif_emisor: str | None, numero: str | None) -> str | None:
        """Fichero ya registrado (válido) con el mismo contenido o el mismo emisor y número."""
        fila = self.con.execute(
            "SELECT fichero FROM facturas WHERE huella = ? AND estado = ? LIMIT 1",
            (huella, Estado.VALIDA.value)).fetchone()
        if fila:
            return fila["fichero"]
        if nif_emisor and numero:
            fila = self.con.execute(
                "SELECT fichero FROM facturas WHERE nif_emisor = ? AND numero = ? AND estado = ? LIMIT 1",
                (nif_emisor, numero, Estado.VALIDA.value)).fetchone()
            if fila:
                return fila["fichero"]
        return None

    # --- escritura y consulta -----------------------------------------------

    def guardar(self, r: Resultado) -> int:
        f = r.factura
        cur = self.con.execute(
            "INSERT INTO facturas (fichero, huella, numero, fecha, emisor, nif_emisor, nif_cliente, base, tipo_iva,"
            " cuota_iva, total, estado, origen_texto, incidencias, procesada_en)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (r.fichero, r.huella, f.numero, f.fecha.isoformat() if f.fecha else None, f.emisor, f.nif_emisor,
             f.nif_cliente, _txt(f.base_imponible), _txt(f.tipo_iva), _txt(f.cuota_iva), _txt(f.total),
             r.estado.value, r.origen_texto, json.dumps(r.incidencias, ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")))
        self.con.commit()
        return cur.lastrowid

    def todas(self) -> list[dict]:
        filas = self.con.execute(f"SELECT {', '.join(COLUMNAS)} FROM facturas ORDER BY id").fetchall()
        res = []
        for fila in filas:
            d = dict(fila)
            d["incidencias"] = json.loads(d["incidencias"])
            res.append(d)
        return res


def _txt(valor) -> str | None:
    return None if valor is None else str(valor)
