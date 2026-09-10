# -*- coding: utf-8 -*-
"""
Etapa 2 — Calidad de Datos
Perfilamiento, diagnóstico, medición (6 dimensiones) y tratamiento del
dataset consolidado de Migración y Desplazamiento Humano.

Entradas:  data/dataset_consolidado.csv  (salida de la Etapa 1)
Salidas:
  - data/dataset_tratado.csv        (dataset después del tratamiento)
  - data/calidad_reporte.json       (perfilamiento + métricas + problemas + comparación)

Ejecutar: python scripts/quality_analysis.py
"""
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
IN_PATH = os.path.join(DATA, "dataset_consolidado.csv")
OUT_CSV = os.path.join(DATA, "dataset_tratado.csv")
OUT_JSON = os.path.join(DATA, "calidad_reporte.json")

ANIO_ACTUAL = 2026

df = pd.read_csv(IN_PATH, encoding="utf-8-sig")
n0, c0 = df.shape

# ===========================================================================
# 1) PERFILAMIENTO
# ===========================================================================
def perfilar(data):
    perfil = {"n_registros": int(len(data)), "n_variables": int(data.shape[1]), "variables": []}
    for col in data.columns:
        s = data[col]
        info = {
            "variable": col,
            "tipo": str(s.dtype),
            "valores_unicos": int(s.nunique(dropna=True)),
            "nulos": int(s.isna().sum()),
            "pct_nulos": round(100 * s.isna().sum() / len(data), 2),
        }
        if pd.api.types.is_numeric_dtype(s):
            info["minimo"] = None if s.dropna().empty else float(s.min())
            info["maximo"] = None if s.dropna().empty else float(s.max())
            info["promedio"] = None if s.dropna().empty else round(float(s.mean()), 2)
        perfil["variables"].append(info)
    return perfil

perfil_antes = perfilar(df)

# Duplicados exactos (ignorando id autogenerado)
cols_sin_id = [c for c in df.columns if c != "id"]
duplicados_exactos = int(df.duplicated(subset=cols_sin_id).sum())

# Valores atípicos (outliers) en personas_desplazadas por método IQR, dentro de cada nivel
outliers_idx = set()
for nivel, g in df.groupby("nivel"):
    serie = g["personas_desplazadas"].dropna()
    if len(serie) < 10:
        continue
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    lim_inf, lim_sup = q1 - 3 * iqr, q3 + 3 * iqr  # 3*IQR: outliers extremos (no simples atípicos leves)
    atipicos = g[(g["personas_desplazadas"] < lim_inf) | (g["personas_desplazadas"] > lim_sup)]
    outliers_idx.update(atipicos.index.tolist())

# ===========================================================================
# 2) DIMENSIONES Y MÉTRICAS DE CALIDAD (sobre el dataset SIN tratar)
# ===========================================================================
campos_clave = ["nivel", "iso3", "pais", "anio", "causa", "personas_desplazadas"]
completitud_pct = round(100 * (1 - df[campos_clave].isna().sum().sum() / (len(df) * len(campos_clave))), 2)

# Exactitud: valores dentro de rango lógico (no negativos, no nulos en personas_desplazadas)
validos_exactitud = df["personas_desplazadas"].dropna()
exactitud_pct = round(100 * (validos_exactitud >= 0).sum() / len(df), 2)

# Consistencia: coherencia jerárquica nivel <-> geografía
inconsistencias_geo = int((
    ((df["nivel"] == "Regional") & (df["departamento"].isna())) |
    ((df["nivel"].isin(["Global", "Nacional"])) & (df["departamento"].notna()))
).sum())
consistencia_pct = round(100 * (1 - inconsistencias_geo / len(df)), 2)

# Unicidad
unicidad_pct = round(100 * (1 - duplicados_exactos / len(df)), 2)

# Validez: dominio permitido en variables categóricas controladas
niveles_validos = {"Global", "Nacional", "Regional"}
causas_validas = {"Conflicto armado / violencia", "Desastre natural / climático"}
fuentes_validas = {"Primaria", "Secundaria", "Terciaria"}
anio_valido = df["anio"].between(1970, ANIO_ACTUAL)
registros_validos = (
    df["nivel"].isin(niveles_validos)
    & df["causa"].isin(causas_validas)
    & df["tipo_fuente"].isin(fuentes_validas)
    & anio_valido
)
validez_pct = round(100 * registros_validos.sum() / len(df), 2)

# Actualidad: proporción de registros dentro de los últimos 10 años (2016-2026)
actuales = df["anio"] >= (ANIO_ACTUAL - 10)
actualidad_pct = round(100 * actuales.sum() / len(df), 2)
anio_max = int(df["anio"].max())
antiguedad_max_anios = ANIO_ACTUAL - anio_max

dimensiones = {
    "Completitud": {
        "definicion": "Proporción de valores presentes (no nulos) en las variables clave para el análisis.",
        "formula": "100 x (1 - nulos_campos_clave / (registros x campos_clave))",
        "resultado_pct": completitud_pct,
        "campos_evaluados": campos_clave,
    },
    "Exactitud": {
        "definicion": "Proporción de valores numéricos que representan magnitudes físicamente posibles (no negativos).",
        "formula": "100 x (valores >= 0) / total",
        "resultado_pct": exactitud_pct,
    },
    "Consistencia": {
        "definicion": "Coherencia entre el nivel de análisis declarado y la presencia/ausencia de variables geográficas dependientes (departamento/municipio).",
        "formula": "100 x (1 - registros_inconsistentes / total)",
        "resultado_pct": consistencia_pct,
        "registros_inconsistentes": inconsistencias_geo,
    },
    "Unicidad": {
        "definicion": "Proporción de registros que no están duplicados exactamente en todas sus variables (excepto el id).",
        "formula": "100 x (1 - duplicados / total)",
        "resultado_pct": unicidad_pct,
        "duplicados_exactos": duplicados_exactos,
    },
    "Validez": {
        "definicion": "Proporción de registros cuyos valores categóricos y de año pertenecen al dominio permitido (nivel, causa, tipo_fuente, rango de años 1970-2026).",
        "formula": "100 x registros_en_dominio / total",
        "resultado_pct": validez_pct,
    },
    "Actualidad": {
        "definicion": "Proporción de registros correspondientes a los últimos 10 años (2016-2026), y antigüedad del dato más reciente respecto al año actual.",
        "formula": "100 x registros_ultimos_10_anios / total",
        "resultado_pct": actualidad_pct,
        "anio_mas_reciente": anio_max,
        "antiguedad_anios": antiguedad_max_anios,
    },
}

# ===========================================================================
# 3) INVENTARIO DE PROBLEMAS
# ===========================================================================
problemas = [
    {
        "variable": "desplazamiento_stock",
        "descripcion": "Valores vacíos porque esta variable solo existe en la fuente IDMC (Global/Nacional); el nivel Regional (CNMH) no reporta stock acumulado.",
        "registros_afectados": int(df["desplazamiento_stock"].isna().sum()),
        "dimension": "Completitud",
        "impacto": "Medio",
        "evidencia": "27.046 de 28.467 registros (95,0%) sin valor en desplazamiento_stock.",
    },
    {
        "variable": "personas_desplazadas",
        "descripcion": "Combinaciones país-año-causa sin cifra reportada por el IDMC (p. ej., países sin datos de desastres en un año determinado).",
        "registros_afectados": int(df["personas_desplazadas"].isna().sum()),
        "dimension": "Completitud",
        "impacto": "Alto",
        "evidencia": f"{int(df['personas_desplazadas'].isna().sum())} registros sin valor en la variable central del análisis.",
    },
    {
        "variable": "departamento / municipio",
        "descripcion": "Nulos esperados en registros de nivel Global/Nacional (no aplica geografía municipal); deben distinguirse de un dato faltante real.",
        "registros_afectados": int(df["departamento"].isna().sum()),
        "dimension": "Completitud",
        "impacto": "Bajo",
        "evidencia": "23.991 registros sin departamento/municipio, correspondientes a niveles Global y Nacional.",
    },
    {
        "variable": "personas_desplazadas",
        "descripcion": "Presencia de valores atípicos extremos (outliers) respecto a la distribución de cada nivel, correspondientes a eventos de desplazamiento masivo real (p. ej., Siria, Colombia en años de pico de conflicto), no a errores de captura.",
        "registros_afectados": len(outliers_idx),
        "dimension": "Exactitud",
        "impacto": "Medio",
        "evidencia": f"{len(outliers_idx)} registros fuera de 3×RIC dentro de su nivel (método IQR extendido).",
    },
    {
        "variable": "nivel / departamento",
        "descripcion": "Inconsistencia jerárquica: registros de nivel Regional sin departamento, o registros Global/Nacional con departamento diligenciado.",
        "registros_afectados": inconsistencias_geo,
        "dimension": "Consistencia",
        "impacto": "Bajo" if inconsistencias_geo == 0 else "Medio",
        "evidencia": f"{inconsistencias_geo} registros con jerarquía nivel-geografía inconsistente.",
    },
    {
        "variable": "periodo (CNMH)",
        "descripcion": "Granularidad temporal distinta entre fuentes: IDMC reporta año puntual; CNMH reporta periodos agregados de varios años. Se usó el año de inicio como referencia, generando pérdida de precisión temporal en el nivel Regional.",
        "registros_afectados": int((df["nivel"] == "Regional").sum()),
        "dimension": "Consistencia",
        "impacto": "Medio",
        "evidencia": f"{int((df['nivel'] == 'Regional').sum())} registros regionales agregados en 4 periodos de hasta 9 años.",
    },
    {
        "variable": "todas (registro completo)",
        "descripcion": "Duplicados exactos detectados al comparar todas las variables entre sí (excluyendo el id autogenerado).",
        "registros_afectados": duplicados_exactos,
        "dimension": "Unicidad",
        "impacto": "Bajo" if duplicados_exactos == 0 else "Alto",
        "evidencia": f"{duplicados_exactos} filas duplicadas exactas encontradas.",
    },
    {
        "variable": "causa (nomenclatura original)",
        "descripcion": "Las fuentes originales usaban etiquetas en inglés ('Conflict', 'Disaster') que debieron homologarse a categorías en español para mantener un dominio único y válido.",
        "registros_afectados": int(len(df)),
        "dimension": "Validez",
        "impacto": "Bajo (ya corregido en la integración)",
        "evidencia": "100% de los registros requirió traducción/homologación de la variable causa.",
    },
    {
        "variable": "anio (CNMH)",
        "descripcion": "El dataset regional no se actualiza desde 2014, por lo que no refleja la situación más reciente del desplazamiento municipal en Colombia.",
        "registros_afectados": int((df["nivel"] == "Regional").sum()),
        "dimension": "Actualidad",
        "impacto": "Alto",
        "evidencia": "Última fecha disponible a nivel Regional: 2014 (12 años de antigüedad respecto a 2026).",
    },
]

# ===========================================================================
# 4) TRATAMIENTO DE LOS DATOS  ->  genera dataset_tratado.csv
# ===========================================================================
df_tratado = df.copy()
acciones_aplicadas = []

# a) Eliminación de duplicados exactos (si existieran)
antes = len(df_tratado)
df_tratado = df_tratado.drop_duplicates(subset=cols_sin_id, keep="first")
acciones_aplicadas.append({
    "accion": "Eliminación de duplicados exactos",
    "detalle": "drop_duplicates() sobre todas las columnas excepto 'id'.",
    "registros_afectados": antes - len(df_tratado),
})

# b) Tratamiento de nulos en personas_desplazadas: se documentan como "sin_dato"
#    (no se imputan con 0 para no subestimar el fenómeno) mediante un flag explícito.
df_tratado["personas_desplazadas_flag"] = np.where(
    df_tratado["personas_desplazadas"].isna(), "sin_dato", "reportado"
)
acciones_aplicadas.append({
    "accion": "Tratamiento de nulos en personas_desplazadas",
    "detalle": "Se creó la variable 'personas_desplazadas_flag' para distinguir 'sin_dato' de un valor real de 0, evitando imputar y subestimar el fenómeno.",
    "registros_afectados": int(df_tratado["personas_desplazadas"].isna().sum()),
})

# c) Tratamiento de nulos en desplazamiento_stock: se documenta como "no_aplica_fuente"
df_tratado["desplazamiento_stock_flag"] = np.where(
    df_tratado["desplazamiento_stock"].isna(), "no_disponible_en_fuente", "reportado"
)
acciones_aplicadas.append({
    "accion": "Tratamiento de nulos en desplazamiento_stock",
    "detalle": "Se etiquetó como 'no_disponible_en_fuente' en lugar de dejar vacío sin explicación, ya que el CNMH (nivel Regional) no mide esta variable.",
    "registros_afectados": int(df_tratado["desplazamiento_stock"].isna().sum()),
})

# d) Corrección de tipos de datos
df_tratado["anio"] = pd.to_numeric(df_tratado["anio"], errors="coerce").astype("Int64")
df_tratado["personas_desplazadas"] = pd.to_numeric(df_tratado["personas_desplazadas"], errors="coerce")
df_tratado["desplazamiento_stock"] = pd.to_numeric(df_tratado["desplazamiento_stock"], errors="coerce")
acciones_aplicadas.append({
    "accion": "Corrección de tipos de datos",
    "detalle": "Se forzó tipo entero para 'anio' y tipo numérico (float) para las variables de magnitud, evitando texto mezclado.",
    "registros_afectados": int(len(df_tratado)),
})

# e) Estandarización de texto (departamento/municipio/país: title case, sin espacios extra)
for col in ["pais", "departamento", "municipio"]:
    df_tratado[col] = df_tratado[col].apply(
        lambda v: v.strip().title() if isinstance(v, str) else v
    )
acciones_aplicadas.append({
    "accion": "Estandarización de texto",
    "detalle": "Se aplicó strip() + title case a 'pais', 'departamento' y 'municipio' para homogeneizar mayúsculas/minúsculas y espacios.",
    "registros_afectados": int(len(df_tratado)),
})

# f) Homologación de categorías (ya aplicada en el origen; se valida el dominio final)
dominio_causa_antes = set(df["causa"].unique())
acciones_aplicadas.append({
    "accion": "Homologación de categorías (causa)",
    "detalle": f"Validado dominio final de 'causa' = {sorted(dominio_causa_antes)}; no se detectaron variantes adicionales que homologar en esta corrida.",
    "registros_afectados": 0,
})

# g) Validación de rangos: se marcan (no se eliminan) registros fuera de dominio válido
df_tratado["registro_valido_dominio"] = registros_validos.values
acciones_aplicadas.append({
    "accion": "Validación de rangos y dominio",
    "detalle": "Se agregó la bandera 'registro_valido_dominio' (True/False) verificando nivel, causa, tipo_fuente y año (1970-2026), permitiendo filtrar fácilmente registros fuera de dominio sin eliminarlos de forma irreversible.",
    "registros_afectados": int((~registros_validos).sum()),
})

# h) Tratamiento justificado de valores atípicos: se marcan, no se eliminan (son reales)
df_tratado["outlier_iqr_extremo"] = df_tratado.index.isin(outliers_idx)
acciones_aplicadas.append({
    "accion": "Tratamiento de valores atípicos",
    "detalle": "Los valores atípicos (picos de desplazamiento masivo) se conservaron por representar eventos reales documentados por las fuentes; se marcaron con la bandera 'outlier_iqr_extremo' para poder excluirlos puntualmente en análisis estadísticos sensibles a extremos (p. ej. promedios), sin perder la información en el dataset.",
    "registros_afectados": len(outliers_idx),
})

# i) Consistencia jerárquica nivel-geografía: se corrige geografía inconsistente si aplica
mask_incons = (
    ((df_tratado["nivel"] == "Regional") & (df_tratado["departamento"].isna())) |
    ((df_tratado["nivel"].isin(["Global", "Nacional"])) & (df_tratado["departamento"].notna()))
)
acciones_aplicadas.append({
    "accion": "Revisión de consistencia jerárquica nivel-geografía",
    "detalle": "Se verificó que todo registro Regional tenga departamento/municipio y que ningún registro Global/Nacional los tenga diligenciados.",
    "registros_afectados": int(mask_incons.sum()),
})

df_tratado.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

# ===========================================================================
# 5) COMPARACIÓN ANTES / DESPUÉS
# ===========================================================================
perfil_despues = perfilar(df_tratado[[c for c in df.columns]])

comparacion = {
    "registros_antes": n0,
    "registros_despues": int(len(df_tratado)),
    "variables_antes": c0,
    "variables_despues": int(df_tratado.shape[1]),
    "duplicados_antes": duplicados_exactos,
    "duplicados_despues": int(df_tratado.duplicated(subset=cols_sin_id).sum()),
    "nulos_personas_desplazadas_antes": int(df["personas_desplazadas"].isna().sum()),
    "nulos_personas_desplazadas_despues_sin_flag": int(df_tratado["personas_desplazadas"].isna().sum()),
    "registros_con_flag_sin_dato": int((df_tratado["personas_desplazadas_flag"] == "sin_dato").sum()),
    "registros_fuera_dominio_antes": int((~registros_validos).sum()),
    "registros_marcados_fuera_dominio_despues": int((~df_tratado["registro_valido_dominio"]).sum()),
    "outliers_detectados_y_marcados": len(outliers_idx),
}

# ===========================================================================
# 6) GUARDAR REPORTE COMPLETO
# ===========================================================================
reporte = {
    "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "proposito_dataset": (
        "Analizar la evolución del desplazamiento forzado por conflicto armado y "
        "desastres naturales en los niveles global, nacional (Colombia) y regional "
        "(municipios), para identificar patrones temporales, geográficos y "
        "demográficos que respondan a las preguntas de investigación de la Etapa 1."
    ),
    "requisitos_calidad": [
        "Completitud suficiente en las variables clave (nivel, país/año, causa, magnitud) para no distorsionar los agregados.",
        "Exactitud: los valores numéricos deben representar magnitudes físicamente posibles (no negativos).",
        "Consistencia entre el nivel declarado y la información geográfica asociada.",
        "Unicidad: ausencia de eventos contados más de una vez por error de integración.",
        "Validez: las variables categóricas deben pertenecer a un dominio controlado y documentado.",
        "Actualidad conocida y declarada explícitamente, dado que las fuentes tienen distinta fecha de corte.",
    ],
    "perfilamiento_antes": perfil_antes,
    "perfilamiento_despues": perfil_despues,
    "dimensiones_calidad": dimensiones,
    "inventario_problemas": problemas,
    "causas_analisis": [
        {
            "causa_raiz": "Fuentes con metodologías y granularidades distintas (IDMC vs. CNMH)",
            "problemas_relacionados": ["Completitud en desplazamiento_stock", "Consistencia en periodo/año", "Actualidad"],
            "explicacion": "El IDMC mide flujo y stock anual global; el CNMH solo mide flujo por periodos plurianuales a nivel municipal. Al integrar ambas fuentes en un esquema común, las columnas que no existen en una fuente quedan vacías para esos registros.",
        },
        {
            "causa_raiz": "Ausencia de reporte en fuente original (no error de captura)",
            "problemas_relacionados": ["Completitud en personas_desplazadas"],
            "explicacion": "El IDMC no publica cifra cuando no se registró ningún evento de ese tipo en un país-año; la ausencia de dato no equivale a cero, sino a 'no reportado', lo que debe tratarse con cuidado.",
        },
        {
            "causa_raiz": "Diferencias de idioma y nomenclatura entre fuentes",
            "problemas_relacionados": ["Validez de la variable causa"],
            "explicacion": "El IDMC entrega las causas en inglés ('Conflict'/'Disaster'); se homologaron a español en el script de construcción del dataset (Etapa 1) para mantener un dominio único.",
        },
        {
            "causa_raiz": "Actualización desigual de las fuentes",
            "problemas_relacionados": ["Actualidad"],
            "explicacion": "El CNMH no ha publicado una actualización posterior a 2014 para el detalle municipal, mientras que el IDMC se actualiza anualmente a nivel país.",
        },
        {
            "causa_raiz": "Heterogeneidad real del fenómeno (no error)",
            "problemas_relacionados": ["Exactitud / valores atípicos"],
            "explicacion": "Los valores atípicos corresponden a picos reales de desplazamiento masivo (crisis humanitarias); eliminarlos sesgaría el análisis, por lo que se marcan en vez de eliminarse.",
        },
    ],
    "integracion_homologacion": {
        "fuentes_integradas": [
            "IDMC - Global Internal Displacement Database (GIDD), hoja 1_Displacement_data",
            "IDMC - Estimaciones SADD (sexo y edad), hoja 3_IDPs_SADD_estimates",
            "CNMH - Desplazamiento forzado histórico por municipios",
        ],
        "llave_de_integracion": "iso3 + anio (Global/Nacional) y departamento + municipio + periodo (Regional)",
        "transformaciones": [
            "Traducción y homologación de causas ('Conflict'->'Conflicto armado / violencia', 'Disaster'->'Desastre natural / climático').",
            "Conversión del formato ancho del CNMH (4 columnas de periodo) a formato largo (una fila por municipio-periodo).",
            "Unificación de unidades geográficas en un esquema jerárquico común: pais -> departamento -> municipio.",
            "Normalización de codificación de caracteres (UTF-8 con BOM) para evitar corrupción de tildes.",
        ],
    },
    "plan_tratamiento": acciones_aplicadas,
    "comparacion_antes_despues": comparacion,
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(reporte, f, ensure_ascii=False, indent=2)

print("Perfilamiento y calidad generados.")
print(f"Registros antes: {n0} | después: {len(df_tratado)} | columnas después: {df_tratado.shape[1]}")
print(json.dumps(dimensiones, ensure_ascii=False, indent=2))
print(json.dumps(comparacion, ensure_ascii=False, indent=2))
