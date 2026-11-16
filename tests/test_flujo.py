import shutil

import pytest
from openpyxl import load_workbook

from facturas.almacen import Almacen
from facturas.flujo import Rutas, procesar_carpeta
from facturas.informe import generar_informe


@pytest.fixture
def procesado(facturas_ejemplo, tmp_path, monkeypatch):
    """Procesa las 9 facturas de ejemplo en una carpeta temporal (sin OCR, para que el test sea estable)."""
    monkeypatch.setattr("facturas.extraccion.ocr_disponible", lambda: False)
    rutas = Rutas(tmp_path / "datos")
    rutas.crear()
    for pdf in facturas_ejemplo.glob("*.pdf"):
        shutil.copy(pdf, rutas.entrada / pdf.name)
    return rutas, {r.fichero: r for r in procesar_carpeta(rutas)}


def test_clasifica_las_facturas(procesado):
    _, res = procesado
    validas = {f for f, r in res.items() if r.estado.value == "valida"}
    assert validas == {"01_suministros_correcta.pdf", "02_papeleria_correcta.pdf",
                       "03_consultoria_correcta.pdf", "04_consultoria_servicios.pdf"}


@pytest.mark.parametrize("fichero,motivo", [
    ("05_error_total_mal_sumado.pdf", "no es la suma"),
    ("06_error_cif_invalido.pdf", "no es válido"),
    ("07_duplicada.pdf", "duplicada"),
    ("08_error_sin_numero.pdf", "número de factura"),
    ("09_escaneada.pdf", "escaneada"),
])
def test_motivos_de_revision(procesado, fichero, motivo):
    _, res = procesado
    assert res[fichero].estado.value == "revision"
    assert any(motivo in i for i in res[fichero].incidencias), res[fichero].incidencias


def test_mueve_los_ficheros_y_deja_la_nota_de_revision(procesado):
    rutas, _ = procesado
    assert not any(rutas.entrada.glob("*.pdf"))
    assert (rutas.procesadas / "2026-11" / "01_suministros_correcta.pdf").exists()
    assert (rutas.procesadas / "2026-10" / "02_papeleria_correcta.pdf").exists()
    nota = (rutas.revision / "05_error_total_mal_sumado.motivo.txt").read_text(encoding="utf-8")
    assert "no es la suma" in nota


def test_volver_a_procesar_la_misma_factura_es_duplicado(procesado, facturas_ejemplo):
    rutas, _ = procesado
    shutil.copy(facturas_ejemplo / "02_papeleria_correcta.pdf", rutas.entrada / "reenvio.pdf")
    (r,) = procesar_carpeta(rutas)
    assert r.estado.value == "revision" and "duplicada" in r.incidencias[0]


def test_informe_excel(procesado, tmp_path):
    rutas, _ = procesado
    with Almacen(rutas.bd) as a:
        salida = generar_informe(a.todas(), tmp_path / "informe.xlsx")
    wb = load_workbook(salida)
    assert wb.sheetnames == ["Facturas válidas", "En revisión", "Resumen por proveedor"]
    assert wb["Facturas válidas"].max_row == 5        # cabecera + 4
    assert wb["En revisión"].max_row == 6             # cabecera + 5
    resumen = list(wb["Resumen por proveedor"].iter_rows(values_only=True))
    assert resumen[-1][0] == "TOTAL" and resumen[-1][2] == 4
    assert resumen[-1][5] == pytest.approx(4589.44)
    assert [fila[0] for fila in resumen[1:-1]].count("Consultoría Norte S.L.") == 1
