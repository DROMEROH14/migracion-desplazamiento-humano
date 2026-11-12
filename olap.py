# -*- coding: utf-8 -*-
"""
Etapa 5 — Motor de análisis multidimensional (OLAP) sobre el modelo estrella en SQLite.

Todas las cifras de las vistas se obtienen con consultas SQL sobre vw_hechos (hecho + 5 dimensiones).
Reglas semánticas aplicadas por el motor (evitan sumar lo que no se puede sumar):
  * Cada medida está atada a su fuente: flujo (GIDD), stock (SADD) y acumulado (CNMH). Nunca se suman fuentes.
  * El stock de SADD solo se suma dentro de un único año (no es aditivo en el tiempo).
  * En SADD «Ambos sexos» ya es Mujeres + Hombres: se usa «Ambos sexos» salvo que la consulta pida sexo.
  * Los porcentajes y promedios se recalculan en cada nivel de agrupación con el denominador indicado.
"""
import math
import os
import sqlite3

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "estrella.db")

# ----------------------------------------------------------------------------------
# Estructura del cubo
# ----------------------------------------------------------------------------------
HIERARQUIAS = {
    "geografia": ["ambito", "pais", "departamento", "municipio"],
    "tiempo": ["ventana", "periodo"],
    "perfil": ["ciclo_vida", "grupo_edad"],
    "fuente": ["institucion", "fuente_corta"],
}
NIVELES = {
    "ambito": ("Geografía", "Ámbito"), "pais": ("Geografía", "País"),
    "departamento": ("Geografía", "Departamento"), "municipio": ("Geografía", "Municipio"),
    "ventana": ("Tiempo", "Ventana de tiempo"), "periodo": ("Tiempo", "Año / periodo"),
    "causa": ("Causa", "Causa"),
    "sexo": ("Perfil", "Sexo"), "ciclo_vida": ("Perfil", "Ciclo de vida"), "grupo_edad": ("Perfil", "Grupo de edad"),
    "institucion": ("Fuente", "Institución"), "fuente_corta": ("Fuente", "Fuente"),
    "tipo_medida": ("Fuente", "Tipo de medida"),
}
ORDEN_FIJO = {
    "ventana": ["Antes de 2009", "2009–2016", "2017–2024", "CNMH 1980–2014"],
    "ciclo_vida": ["Menores de 18", "Adultos 18–59", "Mayores de 60", "No desagregado"],
    "grupo_edad": ["0-4", "5-11", "12-17", "18-59", "60+", "No desagregado"],
    "sexo": ["Mujeres", "Hombres", "Ambos sexos", "No desagregado"],
    "causa": ["Conflicto armado / violencia", "Desastre natural / climático"],
}
CAUSA_C = "Conflicto armado / violencia"
CAUSA_D = "Desastre natural / climático"

# Medidas: (nombre, unidad, fuente, columna, tipo de agregación, ¿suma en el tiempo?)
MEDIDAS = {
    "flujo": dict(nombre="Nuevos desplazamientos", unidad="desplazamientos", fuente="GIDD", col="personas_desplazadas",
                  agg="SUM", suma_tiempo=True),
    "stock": dict(nombre="Personas desplazadas al cierre del año", unidad="personas", fuente="SADD",
                  col="personas_desplazadas", agg="SUM", suma_tiempo=False),
    "stock_gidd": dict(nombre="Stock reportado por GIDD", unidad="personas", fuente="GIDD", col="desplazamiento_stock",
                       agg="SUM", suma_tiempo=False),
    "cnmh": dict(nombre="Desplazados registrados (CNMH)", unidad="desplazamientos", fuente="CNMH",
                 col="personas_desplazadas", agg="SUM", suma_tiempo=True),
    # razones: se calculan con el número de años de los periodos presentes en cada grupo
    "flujo_anual": dict(nombre="Nuevos desplazamientos por año", unidad="desplazamientos/año", fuente="GIDD",
                        col="personas_desplazadas", agg="SUM/AÑOS", suma_tiempo=False),
    "cnmh_anual": dict(nombre="Desplazados registrados por año (CNMH)", unidad="desplazamientos/año", fuente="CNMH",
                       col="personas_desplazadas", agg="SUM/AÑOS", suma_tiempo=False),
}


def con():
    if not (os.path.exists(DB_PATH) and os.path.exists(os.path.join(BASE, "data", "validaciones_estrella.json"))):  # reconstruye el modelo si aún no existe (p. ej. primer arranque en el servidor)
        from etapa5.etl_estrella import main as etl_main
        etl_main()
    c = sqlite3.connect(DB_PATH)
    return c


def _sql_fmt(sql, params):
    out = sql
    for p in params:
        out = out.replace("?", repr(p) if isinstance(p, str) else str(p), 1)
    return out


class Traza:
    """Guarda la última consulta SQL ejecutada (se muestra en la interfaz como evidencia)."""
    def __init__(self):
        self.consultas = []

    def add(self, sql, params):
        self.consultas.append(_sql_fmt(" ".join(sql.split()), params))


def _orden_periodo(c):
    return {r[0]: r[1] for r in c.execute("SELECT periodo, anio_inicio FROM dim_tiempo")}


def agg(medida, por=(), filtros=None, traza=None, anio_def=2024, c=None):
    """Agrega una medida por los niveles `por` aplicando `filtros` {nivel: [valores]}.
    Devuelve (DataFrame[por + valor], notas)."""
    m = MEDIDAS[medida]
    por = list(por)
    filtros = {k: list(v) for k, v in (filtros or {}).items() if v}
    for lvl in list(por) + list(filtros):
        if lvl not in NIVELES:
            raise ValueError("Nivel no permitido: " + lvl)
    donde, params, notas = ["fuente_corta = ?"], [m["fuente"]], []
    if m["fuente"] == "SADD":
        if "sexo" in por or "sexo" in filtros:
            donde.append("sexo IN ('Mujeres','Hombres')")
        else:
            donde.append("sexo = 'Ambos sexos'")
        if "periodo" not in por and len(filtros.get("periodo", [])) != 1:
            filtros["periodo"] = [str(anio_def)]
            notas.append(f"El stock no se suma entre años: se usa un solo corte ({anio_def}).")
    for lvl, vals in filtros.items():
        donde.append(f"{lvl} IN ({','.join('?' * len(vals))})")
        params += vals
    ratio = m["agg"] == "SUM/AÑOS"
    cols_sel = por + (["periodo", "duracion_anios"] if ratio and "periodo" not in por else (["duracion_anios"] if ratio else []))
    cols_sel = list(dict.fromkeys(cols_sel))
    grupo = ", ".join(cols_sel)
    sel = (grupo + ", " if grupo else "") + f"SUM({m['col']}) AS valor, COUNT(*) AS n"
    sql = f"SELECT {sel} FROM vw_hechos WHERE {' AND '.join(donde)}" + (f" GROUP BY {grupo}" if grupo else "")
    cn = c or con()
    df = pd.read_sql(sql, cn, params=params)
    if c is None:
        cn.close()
    if traza is not None:
        traza.add(sql, params)
    if ratio:
        if "periodo" not in df.columns:
            raise ValueError("razón sin periodo")
        base = por
        dur = df.groupby(list(dict.fromkeys(base + ["periodo"])), dropna=False).agg(valor=("valor", "sum"), dur=("duracion_anios", "max"), n=("n", "sum")).reset_index()
        if base:
            df = dur.groupby(base, dropna=False).agg(valor=("valor", "sum"), dur=("dur", "sum"), n=("n", "sum")).reset_index()
        else:
            df = pd.DataFrame([{"valor": dur["valor"].sum(), "dur": dur["dur"].sum(), "n": dur["n"].sum()}])
        df["valor"] = df["valor"] / df["dur"]
        df = df.drop(columns=["dur"])
    elif not por:
        df = df[["valor", "n"]]
    return df, notas


def _escalar(medida, filtros=None, traza=None, **kw):
    df, _ = agg(medida, [], filtros, traza, **kw)
    v = df["valor"].iloc[0] if len(df) else None
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def orden_valores(nivel, vals, c=None):
    vals = list(vals)
    if nivel in ORDEN_FIJO:
        fijo = ORDEN_FIJO[nivel]
        return [x for x in fijo if x in vals] + sorted(x for x in vals if x not in fijo)
    if nivel == "periodo":
        cn = c or con()
        o = _orden_periodo(cn)
        if c is None:
            cn.close()
        return sorted(vals, key=lambda x: (o.get(x, 9999), x))
    return sorted(vals)


def valores(nivel, donde=None):
    """Valores distintos de un nivel (para llenar los filtros). `donde` = {nivel: [valores]} restricción."""
    cn = con()
    cond, params = [], []
    for k, v in (donde or {}).items():
        cond.append(f"{k} IN ({','.join('?' * len(v))})")
        params += v
    sql = f"SELECT DISTINCT {nivel} FROM vw_hechos" + (" WHERE " + " AND ".join(cond) if cond else "")
    vals = [r[0] for r in cn.execute(sql, params)]
    o = orden_valores(nivel, vals, cn)
    cn.close()
    return o


def matriz(medida, filas, cols, filtros=None, modo="valor", top=None, traza=None, anio_def=2024, otros=True):
    """Matriz filas x columnas con totales recalculados al nivel actual.
    modo: 'valor' | 'pct_fila' (denominador: total de la fila) | 'pct_col' (denominador: total de la columna)."""
    cn = con()
    df, notas = agg(medida, [filas, cols], filtros, traza, anio_def, cn)
    tf, _ = agg(medida, [filas], filtros, None, anio_def, cn)
    tc, _ = agg(medida, [cols], filtros, None, anio_def, cn)
    gt = _escalar(medida, filtros, None, anio_def=anio_def)
    ordc = orden_valores(cols, df[cols].dropna().unique().tolist(), cn) if len(df) else []
    tf = tf.sort_values("valor", ascending=False)
    if filas in ORDEN_FIJO or filas == "periodo":
        ordf = orden_valores(filas, tf[filas].dropna().tolist(), cn)
    else:
        ordf = tf[filas].tolist()
    cn.close()
    piv = df.pivot(index=filas, columns=cols, values="valor")
    totf = dict(zip(tf[filas], tf["valor"]))
    totc = dict(zip(tc[cols], tc["valor"]))
    aditiva = MEDIDAS[medida]["agg"] == "SUM"
    filas_vis = ordf if top is None else ordf[:top]
    resto = ordf[len(filas_vis):]
    rows = []

    def celda(v, rt, ct):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        if modo == "pct_fila":
            return None if not rt else v / rt * 100
        if modo == "pct_col":
            return None if not ct else v / ct * 100
        return v

    for r in filas_vis:
        vals = [celda(piv.loc[r, c] if (r in piv.index and c in piv.columns) else None, totf.get(r), totc.get(c)) for c in ordc]
        tot = totf.get(r) if modo == "valor" else (100.0 if modo == "pct_fila" else (totf.get(r) / gt * 100 if gt else None))
        rows.append({"etiqueta": r, "valores": vals, "total": tot})
    if resto and otros and aditiva:
        vals = []
        for c in ordc:
            s = sum(piv.loc[r, c] for r in resto if (r in piv.index and c in piv.columns and not pd.isna(piv.loc[r, c])))
            rt = sum(totf.get(r, 0) for r in resto)
            vals.append(celda(s if s else None, rt, totc.get(c)))
        rt = sum(totf.get(r, 0) for r in resto)
        rows.append({"etiqueta": f"Otros ({len(resto)})", "valores": vals,
                     "total": rt if modo == "valor" else (100.0 if modo == "pct_fila" else (rt / gt * 100 if gt else None))})
    colt = [(totc.get(c) if modo == "valor" else (totc.get(c) / totc.get(c) * 100 if modo == "pct_col" else (totc.get(c) / gt * 100 if gt else None))) for c in ordc]
    return {
        "filas": NIVELES[filas][1], "columnas": NIVELES[cols][1], "col_labels": ordc, "rows": rows,
        "col_totales": colt, "total": gt if modo == "valor" else 100.0, "modo": modo,
        "unidad": MEDIDAS[medida]["unidad"] if modo == "valor" else ("% del total de la fila" if modo == "pct_fila" else "% del total de la columna"),
        "medida": MEDIDAS[medida]["nombre"], "notas": notas,
    }


def top_n(medida, nivel, filtros=None, n=10, traza=None, anio_def=2024, por_extra=None):
    df, notas = agg(medida, [nivel] + (por_extra or []), filtros, traza, anio_def)
    return df, notas


def fmt(n, d=0):
    if n is None:
        return "—"
    s = f"{n:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def pct(a, b, d=1):
    return None if not b else a / b * 100
