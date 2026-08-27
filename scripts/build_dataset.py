# -*- coding: utf-8 -*-
"""
Construcción del dataset consolidado — Etapa 1
Proyecto: Migración y Desplazamiento Humano (Global / Colombia / Regional)

Fuentes originales (crudas), sin modificar:
  - data/idmc_internal_displacement_conflict-violence_disasters-39.xlsx  (IDMC - GIDD, nivel Global/Nacional)
  - data/Desplazamiento_forzado_Hist_C3_B3rico.csv                       (CNMH, nivel Regional - municipios de Colombia)

Salida:
  - data/dataset_consolidado.csv   (dataset integrado, granular)
  - data/diccionario_datos.csv     (diccionario de datos)
  - data/resumen_calidad.json      (diagnóstico inicial de calidad)

Ejecutar:  python scripts/build_dataset.py
"""
import pandas as pd
import numpy as np
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

XLSX_PATH = os.path.join(DATA, "idmc_internal_displacement_conflict-violence_disasters-39.xlsx")
CSV_PATH = os.path.join(DATA, "Desplazamiento_forzado_Hist_C3_B3rico.csv")

rows = []
rid = 1

# ---------------------------------------------------------------------------
# 1) NIVEL GLOBAL / NACIONAL  -> hoja "1_Displacement_data" del IDMC (GIDD)
#    Un registro por país-año-causa (Conflicto / Desastre)
# ---------------------------------------------------------------------------
df1 = pd.read_excel(XLSX_PATH, sheet_name="1_Displacement_data")
df1.columns = [c.strip() for c in df1.columns]

for _, r in df1.iterrows():
    iso3 = r.get("ISO3")
    pais = r.get("Name")
    anio = r.get("Year")
    if pd.isna(iso3) or pd.isna(anio):
        continue
    nivel = "Nacional" if iso3 == "COL" else "Global"

    # --- Causa: Conflicto ---
    flujo_c = r.get("Conflict Internal Displacements")
    stock_c = r.get("Conflict Stock Displacement")
    if pd.notna(flujo_c) or pd.notna(stock_c):
        rows.append({
            "id": rid, "nivel": nivel, "iso3": iso3, "pais": pais,
            "departamento": np.nan, "municipio": np.nan,
            "anio": int(anio), "periodo": str(int(anio)),
            "causa": "Conflicto armado / violencia",
            "sexo": "Todos", "grupo_edad": "Todos",
            "personas_desplazadas": flujo_c if pd.notna(flujo_c) else np.nan,
            "desplazamiento_stock": stock_c if pd.notna(stock_c) else np.nan,
            "duracion_periodo_anios": 1,
            "tipo_fuente": "Secundaria",
            "fuente": "IDMC - Global Internal Displacement Database (GIDD)",
        })
        rid += 1

    # --- Causa: Desastre ---
    flujo_d = r.get("Disaster Internal Displacements")
    stock_d = r.get("Disaster Stock Displacement")
    if pd.notna(flujo_d) or pd.notna(stock_d):
        rows.append({
            "id": rid, "nivel": nivel, "iso3": iso3, "pais": pais,
            "departamento": np.nan, "municipio": np.nan,
            "anio": int(anio), "periodo": str(int(anio)),
            "causa": "Desastre natural / climático",
            "sexo": "Todos", "grupo_edad": "Todos",
            "personas_desplazadas": flujo_d if pd.notna(flujo_d) else np.nan,
            "desplazamiento_stock": stock_d if pd.notna(stock_d) else np.nan,
            "duracion_periodo_anios": 1,
            "tipo_fuente": "Secundaria",
            "fuente": "IDMC - Global Internal Displacement Database (GIDD)",
        })
        rid += 1

# ---------------------------------------------------------------------------
# 2) NIVEL GLOBAL / NACIONAL con desagregación demográfica
#    -> hoja "3_IDPs_SADD_estimates" (sexo y grupo de edad)
# ---------------------------------------------------------------------------
df3 = pd.read_excel(XLSX_PATH, sheet_name="3_IDPs_SADD_estimates")
df3.columns = [c.strip() for c in df3.columns]
age_cols = ["0-4", "5-11", "12-17", "18-59", "60+"]

for _, r in df3.iterrows():
    iso3 = r.get("ISO3")
    pais = r.get("Country")
    anio = r.get("Year")
    sexo = r.get("Sex")
    causa = r.get("Cause")
    if pd.isna(iso3) or pd.isna(anio):
        continue
    nivel = "Nacional" if iso3 == "COL" else "Global"
    causa_es = "Conflicto armado / violencia" if str(causa).strip().lower() == "conflict" else "Desastre natural / climático"

    for age in age_cols:
        val = r.get(age)
        if pd.notna(val):
            rows.append({
                "id": rid, "nivel": nivel, "iso3": iso3, "pais": pais,
                "departamento": np.nan, "municipio": np.nan,
                "anio": int(anio), "periodo": str(int(anio)),
                "causa": causa_es,
                "sexo": sexo if pd.notna(sexo) else "Todos",
                "grupo_edad": age,
                "personas_desplazadas": val,
                "desplazamiento_stock": np.nan,
                "duracion_periodo_anios": 1,
                "tipo_fuente": "Secundaria",
                "fuente": "IDMC - Estimaciones SADD (sexo y edad) de PDI",
            })
            rid += 1

# ---------------------------------------------------------------------------
# 3) NIVEL REGIONAL -> CNMH, desplazamiento forzado histórico por municipio
#    Formato ancho (4 periodos) -> se pasa a formato largo (una fila por
#    municipio-periodo) para ganar granularidad temporal.
# ---------------------------------------------------------------------------
dfc = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
dfc.columns = [c.strip() for c in dfc.columns]

periodo_map = {
    "Periodo_1980_1988": (1980, 1988),
    "Periodo_1989_1996": (1989, 1996),
    "Periodo_1997_2004": (1997, 2004),
    "Periodo_2005_2014": (2005, 2014),
}

for _, r in dfc.iterrows():
    depto = r.get("Departamento")
    muni = r.get("Municipio")
    for col, (y0, y1) in periodo_map.items():
        val = r.get(col)
        if pd.notna(val):
            rows.append({
                "id": rid, "nivel": "Regional", "iso3": "COL", "pais": "Colombia",
                "departamento": depto, "municipio": muni,
                "anio": y0, "periodo": f"{y0}-{y1}",
                "causa": "Conflicto armado / violencia",
                "sexo": "Todos", "grupo_edad": "Todos",
                "personas_desplazadas": val,
                "desplazamiento_stock": np.nan,
                "duracion_periodo_anios": (y1 - y0 + 1),
                "tipo_fuente": "Secundaria",
                "fuente": "CNMH - Desplazamiento forzado histórico por municipios (Una nación desplazada)",
            })
            rid += 1

# ---------------------------------------------------------------------------
# Consolidar
# ---------------------------------------------------------------------------
df = pd.DataFrame(rows)
df["personas_desplazadas"] = pd.to_numeric(df["personas_desplazadas"], errors="coerce")
df["desplazamiento_stock"] = pd.to_numeric(df["desplazamiento_stock"], errors="coerce")
df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")

out_csv = os.path.join(DATA, "dataset_consolidado.csv")
df.to_csv(out_csv, index=False, encoding="utf-8-sig")
print(f"Dataset consolidado: {len(df):,} registros -> {out_csv}")

# ---------------------------------------------------------------------------
# Diccionario de datos
# ---------------------------------------------------------------------------
diccionario = [
    ("id", "Identificador único de registro", "Numérica (entero)", "N/A", "1 - N", "Generado en la consolidación"),
    ("nivel", "Nivel de análisis del registro", "Categórica", "N/A", "Global, Nacional, Regional", "Definido según fuente de origen"),
    ("iso3", "Código ISO3 del país", "Categórica", "N/A", "Ej. COL, VEN, SYR", "IDMC / CNMH"),
    ("pais", "Nombre del país", "Categórica", "N/A", "Nombres de país", "IDMC / CNMH"),
    ("departamento", "Departamento (solo nivel Regional, Colombia)", "Categórica", "N/A", "33 departamentos de Colombia", "CNMH"),
    ("municipio", "Municipio (solo nivel Regional, Colombia)", "Categórica / Geográfica", "N/A", ">1000 municipios de Colombia", "CNMH"),
    ("anio", "Año o año de inicio del periodo", "Temporal", "Año", "1980 - 2024", "IDMC / CNMH"),
    ("periodo", "Año puntual o rango de años del registro", "Temporal (texto)", "N/A", "Ej. 2020, 1997-2004", "IDMC / CNMH"),
    ("causa", "Causa del desplazamiento", "Categórica", "N/A", "Conflicto armado / violencia, Desastre natural / climático", "IDMC / CNMH"),
    ("sexo", "Sexo de la población (si aplica)", "Categórica", "N/A", "Todos, Female, Male, Both sexes", "IDMC (SADD)"),
    ("grupo_edad", "Grupo etario (si aplica)", "Categórica", "N/A", "Todos, 0-4, 5-11, 12-17, 18-59, 60+", "IDMC (SADD)"),
    ("personas_desplazadas", "Número de personas desplazadas / nuevos desplazamientos en el periodo (flujo)", "Numérica (entero)", "Personas", ">= 0", "IDMC / CNMH"),
    ("desplazamiento_stock", "Total acumulado de personas en situación de desplazamiento al cierre del año (stock)", "Numérica (entero)", "Personas", ">= 0 o vacío", "IDMC (solo nivel Global/Nacional)"),
    ("duracion_periodo_anios", "Cantidad de años que cubre el registro", "Numérica (entero)", "Años", "1 - 9", "Calculado"),
    ("tipo_fuente", "Clasificación de la fuente", "Categórica", "N/A", "Primaria, Secundaria, Terciaria", "Documentado en Fuentes"),
    ("fuente", "Nombre de la fuente de datos original", "Categórica", "N/A", "IDMC - GIDD, IDMC - SADD, CNMH", "Documentado en Fuentes"),
]
dicc_df = pd.DataFrame(diccionario, columns=["variable", "descripcion", "tipo", "unidad", "dominio_valores", "procedencia"])
dicc_df.to_csv(os.path.join(DATA, "diccionario_datos.csv"), index=False, encoding="utf-8-sig")
print("Diccionario de datos generado.")

# ---------------------------------------------------------------------------
# Diagnóstico inicial de calidad
# ---------------------------------------------------------------------------
resumen = {
    "total_registros": int(len(df)),
    "registros_por_nivel": df["nivel"].value_counts().to_dict(),
    "registros_por_causa": df["causa"].value_counts().to_dict(),
    "faltantes_personas_desplazadas": int(df["personas_desplazadas"].isna().sum()),
    "faltantes_desplazamiento_stock": int(df["desplazamiento_stock"].isna().sum()),
    "duplicados_exactos": int(df.duplicated(subset=[c for c in df.columns if c != "id"]).sum()),
    "anio_min": int(df["anio"].min()),
    "anio_max": int(df["anio"].max()),
    "paises_distintos": int(df["pais"].nunique()),
    "departamentos_colombia": int(df.loc[df["nivel"] == "Regional", "departamento"].nunique()),
    "municipios_colombia": int(df.loc[df["nivel"] == "Regional", "municipio"].nunique()),
    "valores_negativos_personas": int((df["personas_desplazadas"] < 0).sum()),
}
with open(os.path.join(DATA, "resumen_calidad.json"), "w", encoding="utf-8") as f:
    json.dump(resumen, f, ensure_ascii=False, indent=2)
print("Resumen de calidad generado:")
print(json.dumps(resumen, ensure_ascii=False, indent=2))
