"""Panel web del bot de facturas.

Uso:  streamlit run panel.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

from facturas.almacen import Almacen
from facturas.extraccion import ocr_disponible
from facturas.flujo import Rutas, procesar_carpeta
from facturas.informe import generar_informe

RAIZ = Path(__file__).resolve().parent
rutas = Rutas(RAIZ / "datos")
rutas.crear()

st.set_page_config(page_title="Bot de facturas", page_icon="🧾", layout="wide")
st.title("🧾 Bot de automatización de facturas")
st.caption("Sube facturas en PDF: el bot extrae los datos, los valida y separa las que necesitan revisión.")

# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header("Entrada")
    subidos = st.file_uploader("Añadir facturas (PDF)", type=["pdf"], accept_multiple_files=True)
    if subidos and st.button("Guardar en la carpeta de entrada", width="stretch"):
        for f in subidos:
            (rutas.entrada / f.name).write_bytes(f.getbuffer())
        st.success(f"{len(subidos)} fichero(s) añadidos")

    pendientes = sorted(p.name for p in rutas.entrada.iterdir() if p.suffix.lower() == ".pdf")
    st.write(f"**Pendientes:** {len(pendientes)}")
    if st.button("▶ Procesar pendientes", type="primary", width="stretch", disabled=not pendientes):
        res = procesar_carpeta(rutas)
        st.success(f"{len(res)} procesada(s): {sum(r.estado.value == 'valida' for r in res)} válida(s)")

    if st.button("Cargar facturas de ejemplo", width="stretch"):
        origen = RAIZ / "ejemplos" / "facturas"
        if not origen.exists():
            from ejemplos.generar_facturas import generar
            generar(origen)
        for pdf in origen.glob("*.pdf"):
            shutil.copy(pdf, rutas.entrada / pdf.name)
        st.rerun()

    st.divider()
    st.caption("OCR para escaneados: " + ("✅ disponible" if ocr_disponible() else "❌ instala Tesseract"))

# ---------------------------------------------------------------- datos
with Almacen(rutas.bd) as a:
    facturas = a.todas()

if not facturas:
    st.info("Todavía no hay facturas procesadas. Carga las de ejemplo o sube las tuyas desde la barra lateral.")
    st.stop()

df = pd.DataFrame(facturas)
for c in ("base", "tipo_iva", "cuota_iva", "total"):
    df[c] = pd.to_numeric(df[c])
df["fecha"] = pd.to_datetime(df["fecha"])
validas = df[df["estado"] == "valida"]
revision = df[df["estado"] != "valida"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Facturas procesadas", len(df))
k2.metric("Válidas", len(validas))
k3.metric("En revisión", len(revision))
k4.metric("Importe válido", f"{validas['total'].sum():,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))

pest_validas, pest_revision, pest_graficos = st.tabs(["✔ Válidas", f"⚠ En revisión ({len(revision)})", "📊 Gráficos"])

with pest_validas:
    st.dataframe(
        validas[["numero", "fecha", "emisor", "nif_emisor", "base", "tipo_iva", "cuota_iva", "total", "fichero"]],
        hide_index=True, width="stretch",
        column_config={
            "numero": "Nº factura", "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "emisor": "Emisor", "nif_emisor": "NIF", "tipo_iva": "IVA %",
            "base": st.column_config.NumberColumn("Base", format="%.2f €"),
            "cuota_iva": st.column_config.NumberColumn("Cuota IVA", format="%.2f €"),
            "total": st.column_config.NumberColumn("Total", format="%.2f €"), "fichero": "Fichero",
        })

with pest_revision:
    if revision.empty:
        st.success("No hay facturas pendientes de revisión.")
    for _, f in revision.iterrows():
        with st.expander(f"⚠ {f['fichero']} — {f['emisor'] or 'emisor desconocido'}"):
            for motivo in f["incidencias"]:
                st.write(f"- {motivo}")
            st.caption(f"El PDF está en {rutas.revision / f['fichero']}")

with pest_graficos:
    if validas.empty:
        st.info("Sin facturas válidas todavía.")
    else:
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Total por proveedor")
            # Se agrupa por NIF (único) y se muestra el nombre mejor escrito de cada proveedor
            nombres = validas.groupby("nif_emisor")["emisor"].agg(
                lambda s: next((x for x in s if x and not x.isupper()), s.iloc[0]))
            por_proveedor = validas.groupby("nif_emisor")["total"].sum()
            por_proveedor.index = por_proveedor.index.map(nombres)
            st.bar_chart(por_proveedor.sort_values(ascending=False), horizontal=True)
        with g2:
            st.subheader("Total por mes")
            st.bar_chart(validas.groupby(validas["fecha"].dt.strftime("%Y-%m"))["total"].sum())

informe = generar_informe(facturas, RAIZ / "informes" / "facturas.xlsx")
st.download_button("⬇ Descargar informe Excel", informe.read_bytes(), file_name="facturas.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
