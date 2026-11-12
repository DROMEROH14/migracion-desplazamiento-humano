# -*- coding: utf-8 -*-
"""
Etapa 5 — ETL del modelo estrella (dataset tratado de la Etapa 3  ->  SQLite)

Uso:
    python etapa5/etl_estrella.py            # reconstruye data/estrella.db y data/validaciones_estrella.json

El procedimiento es idempotente: borra y recrea el esquema (sql/01_crear_esquema_estrella.sql)
y vuelve a cargar dimensiones y hechos desde data/dataset_tratado_etapa3.csv.
"""
import json
import os
import sqlite3
import sys

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE, "data", "dataset_tratado_etapa3.csv")
DB_PATH = os.path.join(BASE, "data", "estrella.db")
DDL_PATH = os.path.join(BASE, "etapa5", "sql", "01_crear_esquema_estrella.sql")
VALID_PATH = os.path.join(BASE, "data", "validaciones_estrella.json")

SEXO = {"Female": "Mujeres", "Male": "Hombres", "Both sexes": "Ambos sexos", "Todos": "No desagregado"}
CICLO = {"0-4": "Menores de 18", "5-11": "Menores de 18", "12-17": "Menores de 18",
         "18-59": "Adultos 18–59", "60+": "Mayores de 60", "Todos": "No desagregado"}
ORDEN_EDAD = {"0-4": 1, "5-11": 2, "12-17": 3, "18-59": 4, "60+": 5, "Todos": 9}
FUENTE = {
    "GIDD": ("IDMC", "Flujo anual"),
    "SADD": ("IDMC", "Stock a fin de año"),
    "CNMH": ("CNMH", "Acumulado por periodo"),
}


def _ventana(periodo, anio, fuente_corta):
    if fuente_corta == "CNMH":
        return "CNMH 1980–2014"
    if anio < 2009:
        return "Antes de 2009"
    return "2009–2016" if anio <= 2016 else "2017–2024"


def leer_origen(csv_path=CSV_PATH):
    d = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"periodo": str})
    d["fuente_corta"] = d["fuente"].str.extract(r"(GIDD|SADD|CNMH)")[0]
    assert d["fuente_corta"].notna().all(), "fuente no reconocida"
    return d


def construir_dimensiones(d):
    # ---- dim_tiempo (clave natural: periodo) ----
    t = d[["periodo", "anio", "duracion_periodo_anios", "fuente_corta"]].drop_duplicates(["periodo"]).copy()
    t["anio_inicio"] = t["anio"]
    t["anio_fin"] = t["anio"] + t["duracion_periodo_anios"] - 1
    t["ventana"] = [_ventana(p, a, f) for p, a, f in zip(t["periodo"], t["anio"], t["fuente_corta"])]
    t["decada"] = (t["anio_inicio"] // 10 * 10).astype(str) + "s"
    t = t.sort_values(["anio_inicio", "periodo"]).reset_index(drop=True)
    t.insert(0, "tiempo_key", range(1, len(t) + 1))
    dim_tiempo = t.rename(columns={"duracion_periodo_anios": "duracion_anios"})[
        ["tiempo_key", "periodo", "anio_inicio", "anio_fin", "duracion_anios", "ventana", "decada"]]

    # ---- dim_geografia ----
    g = d[["nivel", "iso3", "pais", "departamento", "municipio"]].copy()
    g["departamento"] = g["departamento"].fillna("No aplica")
    g["municipio"] = g["municipio"].fillna("No aplica")
    g = g.drop_duplicates().sort_values(["nivel", "pais", "departamento", "municipio"]).reset_index(drop=True)
    g["ambito"] = g["pais"].map(lambda x: "Colombia" if x == "Colombia" else "Resto del mundo")
    g.insert(0, "geo_key", range(1, len(g) + 1))
    dim_geo = g[["geo_key", "ambito", "nivel", "iso3", "pais", "departamento", "municipio"]]

    # ---- dim_causa ----
    c = pd.DataFrame({"causa": sorted(d["causa"].unique())})
    c.insert(0, "causa_key", range(1, len(c) + 1))

    # ---- dim_perfil ----
    p = d[["sexo", "grupo_edad"]].drop_duplicates().copy()
    p["sexo_n"] = p["sexo"].map(SEXO)
    p["ciclo_vida"] = p["grupo_edad"].map(CICLO)
    p["orden_edad"] = p["grupo_edad"].map(ORDEN_EDAD)
    p["grupo_edad_n"] = p["grupo_edad"].replace({"Todos": "No desagregado"})
    p = p.sort_values(["orden_edad", "sexo_n"]).reset_index(drop=True)
    p.insert(0, "perfil_key", range(1, len(p) + 1))
    dim_perfil = p.rename(columns={"sexo": "sexo_origen"})[
        ["perfil_key", "sexo_n", "grupo_edad_n", "ciclo_vida", "orden_edad", "sexo_origen", "grupo_edad"]]

    # ---- dim_fuente ----
    f = d[["fuente_corta", "fuente", "tipo_fuente"]].drop_duplicates("fuente_corta").reset_index(drop=True)
    f["institucion"] = f["fuente_corta"].map(lambda x: FUENTE[x][0])
    f["tipo_medida"] = f["fuente_corta"].map(lambda x: FUENTE[x][1])
    f.insert(0, "fuente_key", range(1, len(f) + 1))
    dim_fuente = f.rename(columns={"fuente": "fuente_nombre"})[
        ["fuente_key", "fuente_corta", "fuente_nombre", "institucion", "tipo_medida", "tipo_fuente"]]
    return dim_tiempo, dim_geo, c, dim_perfil, dim_fuente


def construir_hechos(d, dim_tiempo, dim_geo, dim_causa, dim_perfil, dim_fuente):
    x = d.copy()
    x["departamento"] = x["departamento"].fillna("No aplica")
    x["municipio"] = x["municipio"].fillna("No aplica")
    x = x.merge(dim_tiempo[["tiempo_key", "periodo"]], on="periodo", how="left")
    x = x.merge(dim_geo[["geo_key", "nivel", "iso3", "departamento", "municipio"]],
                on=["nivel", "iso3", "departamento", "municipio"], how="left")
    x = x.merge(dim_causa, on="causa", how="left")
    x = x.merge(dim_perfil[["perfil_key", "sexo_origen", "grupo_edad"]],
                left_on=["sexo", "grupo_edad"], right_on=["sexo_origen", "grupo_edad"], how="left")
    x = x.merge(dim_fuente[["fuente_key", "fuente_corta"]], on="fuente_corta", how="left")
    claves = ["tiempo_key", "geo_key", "causa_key", "perfil_key", "fuente_key"]
    if x[claves].isna().any().any():
        raise ValueError("Hay hechos sin clave de dimensión: " + str(x[claves].isna().sum().to_dict()))
    h = pd.DataFrame({
        "hecho_key": range(1, len(x) + 1),
        "tiempo_key": x["tiempo_key"].astype(int), "geo_key": x["geo_key"].astype(int),
        "causa_key": x["causa_key"].astype(int), "perfil_key": x["perfil_key"].astype(int),
        "fuente_key": x["fuente_key"].astype(int),
        "id_origen": x["id"].astype(int), "clave_negocio": x["clave_negocio"],
        "personas_desplazadas": x["personas_desplazadas"],
        "desplazamiento_stock": x["desplazamiento_stock"],
        "duracion_anios": x["duracion_periodo_anios"].astype(int),
        "personas_por_anio": x["personas_desplazadas"] / x["duracion_periodo_anios"],
        "es_outlier": x["outlier_iqr_extremo"].astype(int),
    })
    return h


def cargar(db_path=DB_PATH, csv_path=CSV_PATH, verbose=True):
    d = leer_origen(csv_path)
    dt, dg, dc, dp, dfu = construir_dimensiones(d)
    h = construir_hechos(d, dt, dg, dc, dp, dfu)
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.executescript(open(DDL_PATH, encoding="utf-8").read())
    dt.to_sql("dim_tiempo", con, if_exists="append", index=False)
    dg.to_sql("dim_geografia", con, if_exists="append", index=False)
    dc.to_sql("dim_causa", con, if_exists="append", index=False)
    dp.rename(columns={"sexo_n": "sexo", "grupo_edad_n": "grupo_edad"})[
        ["perfil_key", "sexo", "grupo_edad", "ciclo_vida", "orden_edad"]].to_sql(
        "dim_perfil", con, if_exists="append", index=False)
    dfu.to_sql("dim_fuente", con, if_exists="append", index=False)
    h.to_sql("hechos_desplazamiento", con, if_exists="append", index=False)
    con.commit()
    if verbose:
        for tb in ("dim_tiempo", "dim_geografia", "dim_causa", "dim_perfil", "dim_fuente", "hechos_desplazamiento"):
            print(f"  {tb:24s}", con.execute(f"SELECT COUNT(*) FROM {tb}").fetchone()[0])
    con.close()
    return d


def validar(d, db_path=DB_PATH):
    """Comparaciones entre el modelo y los datos tratados. Devuelve lista de dicts."""
    con = sqlite3.connect(db_path)
    q = lambda s, *a: con.execute(s, a).fetchall()
    one = lambda s, *a: con.execute(s, a).fetchone()[0]
    out = []

    def add(nombre, que, modelo, origen, ok_tol=0.0, nota=""):
        dif = None if (modelo is None or origen is None) else modelo - origen
        ok = dif is not None and abs(dif) <= ok_tol
        out.append({"comprobacion": nombre, "descripcion": que, "modelo": modelo, "origen": origen,
                    "diferencia": dif, "estado": "Correcto" if ok else "Revisar", "nota": nota})

    # --- unicidad de claves ---
    for tb, pk, nat in [("dim_tiempo", "tiempo_key", "periodo"), ("dim_geografia", "geo_key", "nivel||iso3||departamento||municipio"),
                        ("dim_causa", "causa_key", "causa"), ("dim_perfil", "perfil_key", "sexo||'|'||grupo_edad"),
                        ("dim_fuente", "fuente_key", "fuente_corta")]:
        n = one(f"SELECT COUNT(*) FROM {tb}")
        # modelo = claves primarias distintas + claves naturales distintas; origen = 2 × filas (ambas deben igualar las filas)
        add(f"Unicidad de claves de {tb}", f"{n} filas = {n} claves primarias distintas = {n} claves naturales distintas (se muestra la suma de ambas vs 2 × filas)",
            one(f"SELECT COUNT(DISTINCT {pk}) FROM {tb}") + one(f"SELECT COUNT(DISTINCT {nat}) FROM {tb}"), 2 * n)
    # --- integridad referencial ---
    huerf = sum(one(f"SELECT COUNT(*) FROM hechos_desplazamiento f LEFT JOIN {tb} d ON d.{k}=f.{k} WHERE d.{k} IS NULL")
                for tb, k in [("dim_tiempo", "tiempo_key"), ("dim_geografia", "geo_key"), ("dim_causa", "causa_key"),
                              ("dim_perfil", "perfil_key"), ("dim_fuente", "fuente_key")])
    add("Claves foráneas sin dimensión", "Hechos cuya clave no existe en su dimensión", huerf, 0)
    add("PRAGMA foreign_key_check", "Violaciones de claves foráneas reportadas por SQLite", len(q("PRAGMA foreign_key_check")), 0)
    # --- duplicados ---
    add("Duplicados por granularidad", "Grupos repetidos de (tiempo, geografía, causa, perfil, fuente)",
        one("SELECT COUNT(*) FROM (SELECT 1 FROM hechos_desplazamiento GROUP BY tiempo_key,geo_key,causa_key,perfil_key,fuente_key HAVING COUNT(*)>1)"), 0)
    add("Duplicados de clave de negocio", "clave_negocio repetida en la tabla de hechos",
        one("SELECT COUNT(*)-COUNT(DISTINCT clave_negocio) FROM hechos_desplazamiento"), 0)
    # --- conteos y sumas contra el dataset tratado ---
    add("Conteo de registros", "Filas del hecho vs filas del dataset tratado (Etapa 3)",
        one("SELECT COUNT(*) FROM hechos_desplazamiento"), len(d))
    for fc, nom in [("GIDD", "GIDD (flujo)"), ("SADD", "SADD (stock)"), ("CNMH", "CNMH (acumulado)")]:
        add(f"Suma personas_desplazadas — {nom}", "Suma en el modelo vs suma en el dataset tratado",
            one("SELECT SUM(personas_desplazadas) FROM vw_hechos WHERE fuente_corta=?", fc),
            float(d.loc[d.fuente_corta == fc, "personas_desplazadas"].sum()))
    add("Suma desplazamiento_stock (GIDD)", "Suma del stock reportado por GIDD; los NULL no se convierten en cero",
        one("SELECT SUM(desplazamiento_stock) FROM hechos_desplazamiento"), float(d["desplazamiento_stock"].sum()))
    add("Valores de stock no reportados", "Filas con desplazamiento_stock nulo (NULL = no reportado)",
        one("SELECT COUNT(*) FROM hechos_desplazamiento WHERE desplazamiento_stock IS NULL"), int(d["desplazamiento_stock"].isna().sum()))
    add("Categorías 'No desagregado'", "Registros sin sexo/edad (GIDD y CNMH): se conservan como categoría explícita, no como faltante",
        one("SELECT COUNT(*) FROM vw_hechos WHERE sexo='No desagregado' AND grupo_edad='No desagregado'"),
        int(((d.sexo == "Todos") & (d.grupo_edad == "Todos")).sum()))
    # --- coherencia semántica ---
    s24 = one("SELECT SUM(personas_desplazadas) FROM vw_hechos WHERE fuente_corta='SADD' AND periodo='2024' AND nivel<>'Regional' AND sexo='Ambos sexos'")
    mf24 = one("SELECT SUM(personas_desplazadas) FROM vw_hechos WHERE fuente_corta='SADD' AND periodo='2024' AND nivel<>'Regional' AND sexo IN ('Mujeres','Hombres')")
    add("Ambos sexos = Mujeres + Hombres (SADD 2024)", "Evita triplicar el stock al sumar las tres categorías de sexo", s24, mf24,
        ok_tol=max(1.0, 0.0), nota="Diferencia por redondeo de la fuente si no es cero")
    # --- comparación con los tableros de la Etapa 4 ---
    add("Stock PDI 2024 (Etapa 4, Tablero 1)", "Modelo vs valor publicado en Power BI", s24, 83310426.0)
    add("Flujo GIDD 2009–2024 (Etapa 4, Tablero 3)", "Modelo vs total usado en el texto del Tablero 3",
        one("SELECT SUM(personas_desplazadas) FROM vw_hechos WHERE fuente_corta='GIDD' AND anio_inicio>=2009"), 590687264.0)
    add("Total CNMH (Etapa 4, Tablero 2)", "Modelo vs valor publicado en Power BI",
        one("SELECT SUM(personas_desplazadas) FROM vw_hechos WHERE fuente_corta='CNMH'"), 6618594.0)
    con.close()
    return out


def main():
    print("Etapa 5 — cargando el modelo estrella en", DB_PATH)
    d = cargar()
    v = validar(d)
    with open(VALID_PATH, "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=1)
    bad = [x for x in v if x["estado"] != "Correcto"]
    print(f"Validaciones: {len(v)-len(bad)}/{len(v)} correctas")
    for b in bad:
        print("  REVISAR:", b["comprobacion"], b["modelo"], b["origen"])
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
