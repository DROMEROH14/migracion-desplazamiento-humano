# -*- coding: utf-8 -*-
"""
Etapa 1 — Migración y Desplazamiento Humano
Bitácora técnica del proyecto de Minería de Datos (Flask)
"""
import os
import json
import math
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# --------------------------------------------------------------------------
# Carga de datos (una sola vez al iniciar el servidor)
# --------------------------------------------------------------------------
DATASET_PATH = os.path.join(DATA_DIR, "dataset_consolidado.csv")
DICCIONARIO_PATH = os.path.join(DATA_DIR, "diccionario_datos.csv")
CALIDAD_PATH = os.path.join(DATA_DIR, "resumen_calidad.json")
FUENTES_PATH = os.path.join(DATA_DIR, "fuentes.json")

df = pd.read_csv(DATASET_PATH, encoding="utf-8-sig")
df["anio"] = pd.to_numeric(df["anio"], errors="coerce")

dicc_df = pd.read_csv(DICCIONARIO_PATH, encoding="utf-8-sig")

with open(CALIDAD_PATH, encoding="utf-8") as f:
    calidad = json.load(f)

with open(FUENTES_PATH, encoding="utf-8") as f:
    fuentes = json.load(f)

CALIDAD_REPORTE_PATH = os.path.join(DATA_DIR, "calidad_reporte.json")
DATASET_TRATADO_PATH = os.path.join(DATA_DIR, "dataset_tratado.csv")

with open(CALIDAD_REPORTE_PATH, encoding="utf-8") as f:
    calidad_reporte = json.load(f)

NIVELES = ["Global", "Nacional", "Regional"]
CAUSAS = sorted(df["causa"].dropna().unique().tolist())


def kfmt(n):
    """Formatea números grandes (12345678 -> '12.3M')."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000_000:
        return f"{sign}{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{sign}{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{sign}{n/1_000:.1f}K"
    return f"{sign}{n:.0f}"


app.jinja_env.filters["kfmt"] = kfmt


# --------------------------------------------------------------------------
# Agregaciones reutilizables para gráficos (calculadas una vez)
# --------------------------------------------------------------------------
def build_dashboard_aggregates():
    g = df.copy()

    serie_anual = (
        g.groupby(["anio", "nivel"])["personas_desplazadas"]
        .sum()
        .reset_index()
        .dropna(subset=["anio"])
    )
    serie_anual_global = (
        g[g["nivel"] == "Global"].groupby("anio")["personas_desplazadas"].sum().dropna()
    )

    por_causa = g.groupby("causa")["personas_desplazadas"].sum().to_dict()
    por_nivel = g.groupby("nivel")["personas_desplazadas"].sum().to_dict()

    top_paises = (
        g[g["nivel"] == "Global"]
        .groupby("pais")["personas_desplazadas"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    top_departamentos = (
        g[g["nivel"] == "Regional"]
        .groupby("departamento")["personas_desplazadas"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    serie_colombia = (
        g[g["nivel"] == "Nacional"].groupby("anio")["personas_desplazadas"].sum().dropna()
    )

    return {
        "years": sorted(serie_anual_global.index.astype(int).tolist()),
        "global_values": [
            int(serie_anual_global.get(y, 0)) for y in sorted(serie_anual_global.index.astype(int))
        ],
        "por_causa_labels": list(por_causa.keys()),
        "por_causa_values": [int(v) for v in por_causa.values()],
        "por_nivel_labels": list(por_nivel.keys()),
        "por_nivel_values": [int(v) for v in por_nivel.values()],
        "top_paises_labels": top_paises.index.tolist(),
        "top_paises_values": [int(v) for v in top_paises.values],
        "top_departamentos_labels": top_departamentos.index.tolist(),
        "top_departamentos_values": [int(v) for v in top_departamentos.values],
        "colombia_years": sorted(serie_colombia.index.astype(int).tolist()),
        "colombia_values": [
            int(serie_colombia.get(y, 0)) for y in sorted(serie_colombia.index.astype(int))
        ],
    }


AGG = build_dashboard_aggregates()

STATS = {
    "total_registros": int(len(df)),
    "total_personas": int(df["personas_desplazadas"].sum()),
    "paises": int(df["pais"].nunique()),
    "departamentos": int(df.loc[df["nivel"] == "Regional", "departamento"].nunique()),
    "municipios": int(df.loc[df["nivel"] == "Regional", "municipio"].nunique()),
    "anio_min": int(df["anio"].min()),
    "anio_max": int(df["anio"].max()),
    "variables": int(df.shape[1]),
}


# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", stats=STATS, agg=AGG, active="inicio")


@app.route("/problema")
def problema():
    return render_template("problema.html", active="problema")


@app.route("/preguntas")
def preguntas():
    return render_template("preguntas.html", active="preguntas")


@app.route("/necesidades")
def necesidades():
    return render_template("necesidades.html", active="necesidades")


@app.route("/fuentes")
def fuentes_view():
    return render_template("fuentes.html", fuentes=fuentes, active="fuentes")


@app.route("/dataset")
def dataset_view():
    page = request.args.get("page", 1, type=int)
    per_page = 25
    nivel = request.args.get("nivel", "")
    causa = request.args.get("causa", "")
    q = request.args.get("q", "").strip()

    filtered = df
    if nivel in NIVELES:
        filtered = filtered[filtered["nivel"] == nivel]
    if causa in CAUSAS:
        filtered = filtered[filtered["causa"] == causa]
    if q:
        mask = (
            filtered["pais"].astype(str).str.contains(q, case=False, na=False)
            | filtered["departamento"].astype(str).str.contains(q, case=False, na=False)
            | filtered["municipio"].astype(str).str.contains(q, case=False, na=False)
        )
        filtered = filtered[mask]

    total = len(filtered)
    total_pages = max(1, math.ceil(total / per_page))
    page = min(max(page, 1), total_pages)
    start = (page - 1) * per_page
    page_rows = filtered.iloc[start:start + per_page].fillna("")

    return render_template(
        "dataset.html",
        active="dataset",
        columns=list(df.columns),
        rows=page_rows.to_dict(orient="records"),
        page=page,
        total_pages=total_pages,
        total=total,
        nivel=nivel,
        causa=causa,
        q=q,
        niveles=NIVELES,
        causas=CAUSAS,
        stats=STATS,
    )


@app.route("/diccionario")
def diccionario_view():
    return render_template(
        "diccionario.html",
        active="diccionario",
        registros=dicc_df.to_dict(orient="records"),
    )


@app.route("/calidad")
def calidad_view():
    return render_template("calidad.html", active="calidad", calidad=calidad, stats=STATS)


@app.route("/limitaciones")
def limitaciones_view():
    return render_template("limitaciones.html", active="limitaciones")


@app.route("/dataset/descargar")
def descargar_dataset():
    return send_from_directory(DATA_DIR, "dataset_consolidado.csv", as_attachment=True)


@app.route("/calidad-datos")
def calidad_datos_view():
    r = calidad_reporte
    dims = r["dimensiones_calidad"]
    dim_labels = list(dims.keys())
    dim_values = [dims[k]["resultado_pct"] for k in dim_labels]

    comp = r["comparacion_antes_despues"]

    return render_template(
        "calidad_datos.html",
        active="calidad_datos",
        r=r,
        dim_labels=dim_labels,
        dim_values=dim_values,
        comp=comp,
    )


@app.route("/dataset-tratado/descargar")
def descargar_dataset_tratado():
    return send_from_directory(DATA_DIR, "dataset_tratado.csv", as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
