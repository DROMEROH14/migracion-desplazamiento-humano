# -*- coding: utf-8 -*-
"""Etapa 5 — Construcción de las 4 vistas multidimensionales. Todo número sale de consultas a vw_hechos."""
import pandas as pd
import olap
from olap import CAUSA_C, CAUSA_D, agg, matriz, valores, fmt, NIVELES, MEDIDAS, Traza

COL = {"conf": "#ff6b6b", "des": "#5b8cff", "n": "#8b6bff", "m": "#d98bff", "h": "#29d9bd", "gris": "#96a2be"}
CAUSA_COL = {CAUSA_C: COL["conf"], CAUSA_D: COL["des"]}
SEXO_COL = {"Mujeres": COL["m"], "Hombres": COL["h"]}
PAL = ["#5b8cff", "#ff6b6b", "#29d9bd", "#d98bff", "#ffb454", "#8b6bff", "#96a2be", "#7bd88f", "#ff9f7a", "#6fd3ff"]


def f(x):
    try:
        return None if x is None or pd.isna(x) else float(x)
    except Exception:
        return None


def pc(a, b, d=1):
    return None if not b else a / b * 100


def sel_item(nombre, dim, valor, nivel=None):
    return {"filtro": nombre, "dimension": dim, "valor": valor if valor else "Todos", "activo": bool(valor)}


def transponer(m, modo_ui):
    rows = m["rows"]
    nuevas = []
    for j, cl in enumerate(m["col_labels"]):
        nuevas.append({"etiqueta": cl, "valores": [r["valores"][j] for r in rows], "total": m["col_totales"][j]})
    m2 = dict(m)
    m2.update(filas=m["columnas"], columnas=m["filas"], col_labels=[r["etiqueta"] for r in rows], rows=nuevas,
              col_totales=[r["total"] for r in rows])
    return m2


def matriz_ui(medida, filas, cols, filtros, modo, pivot, top, traza, anio_def=2024):
    """Aplica pivot: calcula la matriz original y la transpone, ajustando el denominador de los porcentajes."""
    if pivot:
        orig_modo = {"pct_fila": "pct_col", "pct_col": "pct_fila"}.get(modo, modo)
        m = matriz(medida, filas, cols, filtros, orig_modo, top, traza, anio_def)
        m = transponer(m, modo)
        m["modo"] = modo
        m["unidad"] = MEDIDAS[medida]["unidad"] if modo == "valor" else ("% del total de la fila" if modo == "pct_fila" else "% del total de la columna")
    else:
        m = matriz(medida, filas, cols, filtros, modo, top, traza, anio_def)
    m["pivot"] = bool(pivot)
    return m


def conocimiento(pregunta, dims, proc, evid, hall, interp, util, lim, vista=None, sql=None):
    return {"pregunta": pregunta, "dims": dims, "procedimiento": proc, "evidencia": evid, "hallazgo": hall,
            "interpretacion": interp, "utilidad": util, "limitacion": lim, "vista": vista, "sql": sql}


def barras_h(titulo, labels, vals, unidad, color=None):
    return {"tipo": "bar", "horizontal": True, "titulo": titulo, "labels": labels, "unidad": unidad,
            "datasets": [{"label": unidad, "data": [f(v) for v in vals], "color": color or COL["n"]}]}


# =====================================================================================
# Q1 — Causas del desplazamiento en el tiempo y en el territorio (Tiempo · Causa · Geografía)
# =====================================================================================
def q1(a):
    t = Traza()
    causa = a.get("causa", "")
    ventana = a.get("ventana", "")
    nt = a.get("nivel_t", "ventana")
    ng = a.get("nivel_g", "pais")
    modo = a.get("modo", "valor")
    pivot = a.get("pivot") == "1"
    base_v = ["2009–2016", "2017–2024"]       # periodos equivalentes: 2008 no tiene datos de conflicto
    fv = [ventana] if ventana else base_v
    filt = {"ventana": fv}
    if causa:
        filt["causa"] = [causa]
    filt_sin_causa = {"ventana": fv}
    total, _ = agg("flujo", [], filt, t)
    total = f(total["valor"].iloc[0])
    por_causa, _ = agg("flujo", ["causa"], filt_sin_causa, t)
    pcd = dict(zip(por_causa["causa"], por_causa["valor"]))
    tot_ambas = sum(pcd.values())
    paises, _ = agg("flujo", ["pais"], filt, t)
    paises = paises.sort_values("valor", ascending=False)
    top3 = paises["valor"].head(3).sum()
    kpis = [
        {"titulo": "Nuevos desplazamientos (selección)", "valor": fmt(total), "unidad": "desplazamientos · GIDD · suma de años",
         "nota": "Suma de flujos anuales; un desplazamiento no equivale a una persona única."},
        {"titulo": "Participación del conflicto", "valor": fmt(pc(pcd.get(CAUSA_C, 0), tot_ambas), 1) + " %", "unidad": "% del flujo total de la(s) ventana(s)",
         "nota": "Denominador: conflicto + desastres de las ventanas elegidas (no cambia con el filtro de causa)."},
        {"titulo": "Concentración en los 3 países principales", "valor": fmt(pc(top3, total), 1) + " %",
         "unidad": f"% de la selección · {len(paises)} países con registro",
         "nota": "Denominador: total de la selección; conteo de países distintos, no de registros."},
    ]
    # gráfico 1: serie temporal apilada por causa al nivel temporal elegido
    ser, _ = agg("flujo", [nt, "causa"], {**filt_sin_causa, **({"causa": [causa]} if causa else {})}, t)
    etq = olap.orden_valores(nt, ser[nt].unique().tolist())
    ds = []
    for cz in olap.ORDEN_FIJO["causa"]:
        if causa and cz != causa:
            continue
        d = ser[ser["causa"] == cz].set_index(nt)["valor"]
        ds.append({"label": cz, "data": [f(d.get(e)) for e in etq], "color": CAUSA_COL[cz]})
    g1 = {"tipo": "bar", "stacked": True, "titulo": f"Nuevos desplazamientos por {NIVELES[nt][1].lower()} y causa", "labels": etq,
          "datasets": ds, "unidad": "desplazamientos"}
    # gráfico 2: ranking del nivel geográfico
    lg = ng if ng in ("pais", "ambito") else "pais"
    rk, _ = agg("flujo", [lg], filt, t)
    rk = rk.sort_values("valor", ascending=False).head(10)
    g2 = barras_h(f"Principales {'países' if lg == 'pais' else 'ámbitos'} por nuevos desplazamientos", rk[lg].tolist(), rk["valor"].tolist(), "desplazamientos",
                  CAUSA_COL.get(causa, COL["n"]))
    mat = matriz_ui("flujo", ng, "causa", filt, modo, pivot, 8 if ng == "pais" else None, t)
    # interpretación dinámica
    ratio = pcd.get(CAUSA_C, 0)
    interp = (f"Con la selección activa ({'ventana ' + ventana if ventana else 'ventanas 2009–2016 y 2017–2024'}; "
              f"{causa or 'ambas causas'}), el modelo suma {fmt(total)} nuevos desplazamientos. "
              f"Los tres países principales concentran {fmt(pc(top3, total), 1)} % del total. "
              "Al pasar de país a ámbito (roll-up) la matriz se recalcula y los porcentajes cambian porque cambia el denominador; "
              "al pasar de ventana a año (drill-down) se ve en qué años se concentra el aumento.")
    return dict(
        id="q1", titulo="Causas del desplazamiento: ¿cuándo, dónde y por qué cambió el flujo mundial?",
        pregunta="¿Cómo se distribuyen los nuevos desplazamientos entre conflicto y desastres, y cuánto de ese flujo se concentra en pocos países, al comparar las ventanas 2009–2016 y 2017–2024?",
        dims="Tiempo · Causa · Geografía", medidas="Nuevos desplazamientos (GIDD)", jerarquias="Tiempo: ventana → año · Geografía: ámbito → país",
        profundiza="El tablero evidente mostraba el total por causa; aquí se cruzan causa × ventana × país para ver si el aumento reciente del conflicto es general o está concentrado.",
        seleccion=[sel_item("Causa", "Causa", causa), sel_item("Ventana", "Tiempo", ventana or "2009–2016 y 2017–2024"),
                   {"filtro": "Nivel temporal", "dimension": "Tiempo", "valor": NIVELES[nt][1], "activo": True},
                   {"filtro": "Nivel geográfico", "dimension": "Geografía", "valor": NIVELES[ng][1], "activo": True}],
        filtros=[{"name": "causa", "label": "Causa", "dim": "Causa", "value": causa, "opts": [("", "Ambas")] + [(c, c) for c in olap.ORDEN_FIJO["causa"]]},
                 {"name": "ventana", "label": "Ventana de tiempo", "dim": "Tiempo", "value": ventana, "opts": [("", "Ambas")] + [(v, v) for v in base_v]}],
        controles=[{"name": "nivel_t", "label": "Nivel de Tiempo (drill-down / roll-up)", "value": nt, "opts": [("ventana", "Ventana (general)"), ("periodo", "Año (detalle)")]},
                   {"name": "nivel_g", "label": "Nivel de Geografía (drill-down / roll-up)", "value": ng, "opts": [("ambito", "Ámbito (general)"), ("pais", "País (detalle)")]},
                   {"name": "modo", "label": "Valores de la matriz", "value": modo, "opts": [("valor", "Valores absolutos"), ("pct_fila", "% de la fila"), ("pct_col", "% de la columna")]}],
        pivot=pivot, kpis=kpis, charts=[g1, g2], matriz=mat, interpretacion=interp, sql=t.consultas[:6],
        limitacion="El flujo suma desplazamientos, no personas únicas: una persona desplazada varias veces cuenta varias veces. 2008 se excluye porque no tiene datos de conflicto, de modo que las ventanas comparadas son de 8 años cada una. Los datos de conflicto de IDMC dependen de la cobertura de reportes por país.",
        decision="Priorizar el monitoreo y la preparación humanitaria en los pocos países que concentran cerca de la mitad del flujo de cada causa (por ejemplo, planes de respuesta para desastres en Filipinas, China e India y para conflicto en RD Congo y Ucrania), sin descuidar la larga cola de países con flujos menores.",
        conocimientos=q1_conocimientos())


def q1_conocimientos():
    t = Traza()
    d, _ = agg("flujo", ["ventana", "causa"], {"ventana": ["2009–2016", "2017–2024"]}, t)
    g = {(r.ventana, r.causa): r.valor for r in d.itertuples()}
    c1, c2 = g[("2009–2016", CAUSA_C)], g[("2017–2024", CAUSA_C)]
    d1, d2 = g[("2009–2016", CAUSA_D)], g[("2017–2024", CAUSA_D)]
    s1, s2 = pc(c1, c1 + d1), pc(c2, c2 + d2)
    y, _ = agg("flujo", ["periodo"], {"causa": [CAUSA_C], "periodo": [str(x) for x in range(2017, 2025)]}, t)
    ymax = y.sort_values("valor", ascending=False).iloc[0]
    pais22, _ = agg("flujo", ["pais"], {"causa": [CAUSA_C], "periodo": ["2022"]}, t)
    pais22 = pais22.sort_values("valor", ascending=False)
    uk = pais22.iloc[0]
    k1 = conocimiento(
        "¿El aumento del desplazamiento por conflicto entre 2009–2016 y 2017–2024 es mayor que el de los desastres, y en qué año se concentra?",
        "Tiempo (ventana → año) · Causa · medida: nuevos desplazamientos (suma, GIDD)",
        "Roll-up de año a ventana (dos ventanas de 8 años equivalentes) agrupado por causa; luego drill-down al año con mayor flujo de conflicto en 2017–2024 y slice del país líder de ese año.",
        "Vista 1, gráfico «por ventana y causa» y matriz país × causa. Consulta: SUM(personas_desplazadas) GROUP BY ventana, causa con fuente = GIDD.",
        f"El conflicto pasó de {fmt(c1)} a {fmt(c2)} desplazamientos (×{fmt(c2 / c1, 2)}), mientras los desastres pasaron de {fmt(d1)} a {fmt(d2)} (×{fmt(d2 / d1, 2)}). La participación del conflicto subió de {fmt(s1, 1)} % a {fmt(s2, 1)} %. El pico de conflicto de 2017–2024 es {ymax.periodo} con {fmt(ymax.valor)}, y {uk.pais} aporta {fmt(uk.valor)} ({fmt(pc(uk.valor, ymax.valor), 1)} %) de ese año.",
        "El crecimiento reciente es principalmente un fenómeno de conflicto y está concentrado en un año y un país, lo que el total por causa de la etapa 4 no permitía ver. El aumento no es una tendencia uniforme.",
        "Permite orientar recursos de respuesta a crisis de conflicto agudo (picos) frente a una carga más estable de desastres.",
        "Describe asociación temporal con los datos reportados; no explica por qué aumentó el conflicto ni prueba que 2022 sea un cambio permanente.", "q1", t.consultas[:3])
    t2 = Traza()
    res = {}
    for cz, nom in ((CAUSA_C, "conflicto"), (CAUSA_D, "desastres")):
        p, _ = agg("flujo", ["pais"], {"causa": [cz], "ventana": ["2017–2024"]}, t2)
        p = p.sort_values("valor", ascending=False)
        tot = p["valor"].sum()
        res[nom] = dict(n=len(p), top3=pc(p["valor"].head(3).sum(), tot), top5=pc(p["valor"].head(5).sum(), tot),
                        l3=", ".join(p["pais"].head(3)), v1=p.iloc[0])
    k2 = conocimiento(
        "¿Qué tan concentrado está el flujo de 2017–2024 en pocos países según la causa?",
        "Geografía (país) · Causa · medida: nuevos desplazamientos; indicador derivado: % acumulado de los países principales",
        "Slice de la ventana 2017–2024; agrupación por país dentro de cada causa; ordenamiento descendente y cálculo del % acumulado de los 3 y 5 primeros (denominador: total de la causa en la ventana).",
        "Vista 1, ranking de países (filtro Causa = cada valor) y matriz país × causa en modo «% de la columna».",
        f"Conflicto: {res['conflicto']['n']} países con registro; los 3 primeros ({res['conflicto']['l3']}) suman {fmt(res['conflicto']['top3'], 1)} % y los 5 primeros {fmt(res['conflicto']['top5'], 1)} %. Desastres: {res['desastres']['n']} países; los 3 primeros ({res['desastres']['l3']}) suman {fmt(res['desastres']['top3'], 1)} % y los 5 primeros {fmt(res['desastres']['top5'], 1)} %.",
        "La concentración relativa es parecida en ambas causas, pero el conflicto la alcanza con muchos menos países afectados: los desastres son más extendidos geográficamente y el conflicto más focalizado.",
        "Sugiere estrategias distintas: respuesta focalizada y sostenida en pocos países para conflicto; alertas amplias y mecanismos de reacción rápida para desastres.",
        "La concentración depende de la cobertura y de la forma de reportar de cada país; no mide la gravedad per cápita, pues no se normaliza por población.", "q1", t2.consultas[:2])
    return [k1, k2]


# =====================================================================================
# Q2 — Territorio y periodos del desplazamiento en Colombia (CNMH)
# =====================================================================================
def q2(a):
    t = Traza()
    periodo = a.get("periodo", "")
    depto = a.get("depto", "")
    nivel = a.get("nivel", "departamento")
    medida = a.get("medida", "cnmh")
    modo = a.get("modo", "valor")
    pivot = a.get("pivot") == "1"
    if nivel == "municipio" and not depto:
        pass
    filt = {}
    if periodo:
        filt["periodo"] = [periodo]
    if depto:
        filt["departamento"] = [depto]
    um = MEDIDAS[medida]["unidad"]
    tot_df, _ = agg(medida, [], filt, t)
    total = f(tot_df["valor"].iloc[0])
    reg = int(tot_df["n"].iloc[0]) if "n" in tot_df else 0
    un, _ = agg(medida, [nivel], filt, t)
    un = un[un["valor"] > 0].sort_values("valor", ascending=False)
    suma_un = un["valor"].sum()
    if medida == "cnmh":
        top3 = pc(un["valor"].head(3).sum(), total)
    else:
        top3 = pc(un["valor"].head(3).sum(), un["valor"].sum()) if suma_un else None
    kpis = [
        {"titulo": "Desplazados registrados (selección)" if medida == "cnmh" else "Registrados por año (selección)",
         "valor": fmt(total), "unidad": um + " · CNMH", "nota": "Registros acumulados por periodo; por año = total ÷ años de los periodos incluidos."},
        {"titulo": f"{NIVELES[nivel][1]}s con registro", "valor": fmt(len(un)), "unidad": f"conteo distinto de {NIVELES[nivel][1].lower()}s con valor > 0",
         "nota": f"{reg} filas del hecho (conteo de registros) → {len(un)} unidades distintas."},
        {"titulo": "Peso de las 3 primeras unidades", "valor": fmt(top3, 1) + " %" if top3 is not None else "—",
         "unidad": f"% del total de la selección ({NIVELES[nivel][1].lower()})", "nota": "Denominador: suma de las unidades de la selección."},
    ]
    top = un.head(10)
    g1 = barras_h(f"Principales {NIVELES[nivel][1].lower()}s — {um}", top[nivel].tolist(), top["valor"].tolist(), um, COL["conf"])
    # gráfico 2: evolución de la participación por periodo (denominador = total del alcance en cada periodo)
    alc = {"departamento": [depto]} if depto else {}
    sp, _ = agg("cnmh", [nivel, "periodo"], alc, t)
    totp, _ = agg("cnmh", ["periodo"], alc, t)
    tp = dict(zip(totp["periodo"], totp["valor"]))
    base_rank, _ = agg("cnmh", [nivel], alc, t)
    cand = base_rank.sort_values("valor", ascending=False)[nivel].head(5).tolist()
    pers = olap.orden_valores("periodo", list(tp))
    ds = []
    for i, c in enumerate(cand):
        d = sp[sp[nivel] == c].set_index("periodo")["valor"]
        ds.append({"label": c, "data": [f(pc(d.get(p, 0), tp[p])) if p in d else 0 for p in pers], "color": PAL[i % len(PAL)]})
    alcance = f"dentro de {depto}" if depto else "del total nacional"
    g2 = {"tipo": "line", "titulo": f"Participación de las 5 principales unidades {alcance}, por periodo (%)", "labels": pers, "datasets": ds,
          "unidad": "% del total del periodo " + alcance}
    mat = matriz_ui(medida, nivel, "periodo", {k: v for k, v in filt.items() if k != "periodo"} if not periodo else filt,
                    modo, pivot, 10, t)
    interp = (f"Con la selección ({periodo or 'los 4 periodos'}; {depto or 'todo el país'}; nivel {NIVELES[nivel][1].lower()}) "
              f"el modelo reporta {fmt(total)} {um}. Las 3 primeras unidades suman {fmt(top3, 1) if top3 is not None else '—'} %. "
              "La matriz permite comparar la misma unidad entre periodos: como los periodos duran 9, 8, 8 y 10 años, "
              "la medida «por año» evita que el periodo más largo parezca el más grave.")
    return dict(
        id="q2", titulo="Territorio y periodos: ¿dónde se concentró el desplazamiento en Colombia y cómo se movió?",
        pregunta="¿Cómo cambió la participación de cada departamento (y de sus municipios) en el desplazamiento registrado por el CNMH entre los cuatro periodos 1980–2014?",
        dims="Geografía (departamento → municipio) · Tiempo (periodo CNMH) · Fuente (CNMH)", medidas="Desplazados registrados; registrados por año; % del periodo",
        jerarquias="Geografía: ámbito → departamento → municipio · Tiempo: ventana CNMH → periodo",
        profundiza="La etapa 4 mostró «Antioquia primero» y el total por periodo; aquí se mide cómo cambió su peso periodo a periodo y qué municipios lo explican.",
        seleccion=[sel_item("Periodo", "Tiempo", periodo), sel_item("Departamento", "Geografía", depto),
                   {"filtro": "Nivel geográfico", "dimension": "Geografía", "valor": NIVELES[nivel][1], "activo": True},
                   {"filtro": "Medida", "dimension": "Medida", "valor": MEDIDAS[medida]["nombre"], "activo": True}],
        filtros=[{"name": "periodo", "label": "Periodo CNMH", "dim": "Tiempo", "value": periodo,
                  "opts": [("", "Todos")] + [(p, p) for p in olap.orden_valores("periodo", valores("periodo", {"fuente_corta": ["CNMH"]}))]},
                 {"name": "depto", "label": "Departamento", "dim": "Geografía", "value": depto,
                  "opts": [("", "Todos")] + [(d, d) for d in valores("departamento", {"fuente_corta": ["CNMH"]})]}],
        controles=[{"name": "nivel", "label": "Nivel de Geografía (drill-down / roll-up)", "value": nivel, "opts": [("departamento", "Departamento (general)"), ("municipio", "Municipio (detalle)")]},
                   {"name": "medida", "label": "Medida", "value": medida, "opts": [("cnmh", "Registrados (suma)"), ("cnmh_anual", "Registrados por año")]},
                   {"name": "modo", "label": "Valores de la matriz", "value": modo, "opts": [("valor", "Valores absolutos"), ("pct_col", "% del periodo (columna)"), ("pct_fila", "% de la unidad (fila)")]}],
        pivot=pivot, kpis=kpis, charts=[g1, g2], matriz=mat, interpretacion=interp, sql=t.consultas[:6],
        limitacion="El CNMH registra hechos reportados y documentados, con subregistro conocido en los primeros periodos; los periodos tienen distinta duración y el municipio asignado es el de ocurrencia del hecho. El conteo es de desplazamientos registrados, no de personas únicas.",
        decision="Focalizar los programas de reparación y restitución en los municipios que concentran la mayor parte del registro dentro de cada departamento, revisando cada periodo, en lugar de asignar recursos solo por el total departamental.",
        conocimientos=q2_conocimientos())


def q2_conocimientos():
    t = Traza()
    sp, _ = agg("cnmh", ["departamento", "periodo"], {}, t)
    tp = sp.groupby("periodo")["valor"].sum()
    ant = sp[sp.departamento == "Antioquia"].set_index("periodo")["valor"]
    pers = olap.orden_valores("periodo", list(tp.index))
    sh = {p: pc(ant.get(p, 0), tp[p]) for p in pers}
    other = {}
    for dpt in ("Córdoba", "Nariño", "Valle Del Cauca"):
        s = sp[sp.departamento == dpt].set_index("periodo")["valor"]
        other[dpt] = {p: pc(s.get(p, 0), tp[p]) for p in pers}
    k1 = conocimiento(
        "¿Cómo cambió el peso de Antioquia en el desplazamiento registrado entre periodos y qué departamentos ganaron participación?",
        "Geografía (departamento) · Tiempo (periodo) · medida: desplazados registrados; % del total del periodo",
        "Agrupación por departamento × periodo; porcentaje calculado con denominador = total nacional de cada periodo (no se promedian porcentajes).",
        "Vista 2, matriz departamento × periodo en modo «% del periodo» y gráfico de participación.",
        "Antioquia: " + " → ".join(f"{fmt(sh[p], 1)} %" for p in pers) + " (" + ", ".join(pers) + "). "
        + " ".join(f"{k}: {fmt(v[pers[0]], 1)} % → {fmt(v[pers[-1]], 1)} %." for k, v in other.items()),
        "El desplazamiento no se concentró siempre en el mismo lugar: Antioquia alcanza su máximo relativo en el periodo central y luego baja mientras departamentos como Nariño y Valle del Cauca ganan participación. El «Antioquia primero» de la etapa 4 es válido para el total, pero no para cada periodo.",
        "Los programas territoriales deben revisarse por periodo; un diagnóstico solo con el acumulado sobrerrepresenta zonas que fueron críticas en un momento específico.",
        "La participación relativa no indica gravedad absoluta ni causas; un cambio de peso puede deberse a mejoras de registro en otras zonas (hipótesis no comprobada con estos datos).", "q2", t.consultas[:2])
    t2 = Traza()
    mun, _ = agg("cnmh", ["municipio"], {"departamento": ["Antioquia"]}, t2)
    mun = mun.sort_values("valor", ascending=False)
    tot = mun["valor"].sum()
    top3 = mun.head(3)
    m89, _ = agg("cnmh", ["municipio"], {"departamento": ["Antioquia"], "periodo": ["1989-1996"]}, t2)
    m89 = m89.sort_values("valor", ascending=False)
    tot89 = m89["valor"].sum()
    k2 = conocimiento(
        "Dentro de Antioquia, ¿el desplazamiento se concentra en pocos municipios y varía según el periodo?",
        "Geografía (departamento → municipio) · Tiempo (periodo) · medida: desplazados registrados",
        "Slice departamento = Antioquia; drill-down de departamento a municipio; dice con periodo 1989-1996; porcentajes con denominador = total de Antioquia (o de Antioquia en el periodo).",
        "Vista 2 con filtros Departamento = Antioquia, nivel Municipio; el gráfico de barras y la matriz municipio × periodo respaldan las cifras.",
        f"Antioquia suma {fmt(tot)}; los 3 primeros municipios ({', '.join(top3['municipio'])}) aportan {fmt(pc(top3['valor'].sum(), tot), 2)} % y el primero ({top3.iloc[0]['municipio']}) {fmt(pc(top3.iloc[0]['valor'], tot), 1)} %. En 1989-1996 los 3 primeros ({', '.join(m89['municipio'].head(3))}) suman {fmt(pc(m89['valor'].head(3).sum(), tot89), 1)} % del total de Antioquia en ese periodo ({len(m89)} municipios con registro).",
        "El patrón departamental esconde focos municipales: la concentración es mayor cuando se mira un periodo concreto que cuando se mira el acumulado, y los municipios líderes cambian de un periodo a otro.",
        "Orienta a priorizar subregiones y municipios específicos por periodo para memoria histórica, atención y restitución.",
        "El registro municipal puede verse afectado por la forma de georreferenciar los hechos; la concentración no demuestra causalidad ni responsabilidad.", "q2", t2.consultas[:3])
    return [k1, k2]


# =====================================================================================
# Q3 — Perfil de la población desplazada (SADD): sexo · edad · causa · país
# =====================================================================================
def q3(a):
    t = Traza()
    causa = a.get("causa", "")
    anio = a.get("anio", "2024")
    pais = a.get("pais", "")
    nivel = a.get("nivel", "ciclo_vida")
    colsd = a.get("cols", "causa")
    modo = a.get("modo", "pct_col")
    pivot = a.get("pivot") == "1"
    filt = {"periodo": [anio]}
    if causa:
        filt["causa"] = [causa]
    if pais:
        filt["pais"] = [pais]
    tot = f(agg("stock", [], filt, t)[0]["valor"].iloc[0])
    cv, _ = agg("stock", ["ciclo_vida"], filt, t)
    cvd = dict(zip(cv["ciclo_vida"], cv["valor"]))
    sx, _ = agg("stock", ["sexo"], filt, t)
    sxd = dict(zip(sx["sexo"], sx["valor"]))
    m60, _ = agg("stock", ["ciclo_vida", "sexo"], filt, t)
    m60 = m60[m60.ciclo_vida == "Mayores de 60"].set_index("sexo")["valor"]
    kpis = [
        {"titulo": "Personas desplazadas internas al cierre", "valor": fmt(tot), "unidad": f"personas · SADD · corte {anio}",
         "nota": "Stock a fin de año (no se suma entre años); se usa «Ambos sexos» para no triplicar."},
        {"titulo": "Menores de 18 años", "valor": fmt(pc(cvd.get("Menores de 18", 0), tot), 1) + " %", "unidad": "% del stock de la selección",
         "nota": "Denominador: stock total de la selección en el año elegido."},
        {"titulo": "Mujeres entre los mayores de 60", "valor": fmt(pc(m60.get("Mujeres", 0), m60.get("Mujeres", 0) + m60.get("Hombres", 0)), 1) + " %",
         "unidad": "% de mujeres sobre (mujeres + hombres) de 60+", "nota": "Denominador: mujeres + hombres de 60+ con sexo desagregado."},
    ]
    st, _ = agg("stock", [nivel, "sexo"], filt, t)
    etq = olap.orden_valores(nivel, st[nivel].unique().tolist())
    ds = []
    for sx_ in ("Mujeres", "Hombres"):
        d = st[st.sexo == sx_].set_index(nivel)["valor"]
        ds.append({"label": sx_, "data": [f(d.get(e)) for e in etq], "color": SEXO_COL[sx_]})
    g1 = {"tipo": "bar", "stacked": False, "titulo": f"Personas desplazadas por {NIVELES[nivel][1].lower()} y sexo ({anio})", "labels": etq,
          "datasets": ds, "unidad": "personas"}
    # ranking de países por % de menores (stock ≥ umbral) — respeta año y causa, ignora el filtro de país
    f_r = {"periodo": [anio]}
    if causa:
        f_r["causa"] = [causa]
    pr, _ = agg("stock", ["pais", "ciclo_vida"], f_r, t)
    pv = pr.pivot(index="pais", columns="ciclo_vida", values="valor").fillna(0)
    pv["total"] = pv.sum(axis=1)
    umbral = 500000
    pv = pv[pv["total"] >= umbral]
    pv["pct"] = pv["Menores de 18"] / pv["total"] * 100
    alto = pv.sort_values("pct", ascending=False).head(5)
    bajo = pv.sort_values("pct").head(5)
    sel = pd.concat([alto, bajo.iloc[::-1]])
    g2 = barras_h(f"% de menores de 18 — 5 mayores y 5 menores (países con ≥ {fmt(umbral)} desplazados)", sel.index.tolist(), sel["pct"].tolist(), "% de menores de 18", COL["h"])
    g2["nota"] = "Este ranking respeta el año y la causa, pero no el filtro de país."
    cols_dim = "causa" if colsd == "causa" else "sexo"
    mf = {k: v for k, v in filt.items() if k != "causa"} if cols_dim == "causa" and False else filt
    mat = matriz_ui("stock", nivel, cols_dim, mf, modo, pivot, None, t)
    interp = (f"En {anio}, con la selección ({causa or 'ambas causas'}; {pais or 'todos los países'}), el stock es {fmt(tot)} personas; "
              f"{fmt(pc(cvd.get('Menores de 18', 0), tot), 1)} % son menores de 18 años. "
              "Al cambiar de ciclo de vida a grupo de edad (drill-down) la matriz recalcula los porcentajes con el mismo denominador "
              "(columna) y permite ver si los menores se concentran en la primera infancia o en la adolescencia.")
    return dict(
        id="q3", titulo="Perfil de la población desplazada: ¿quiénes son según edad, sexo y causa?",
        pregunta="¿Cómo cambia la composición por ciclo de vida y sexo del desplazamiento interno según la causa y el país, en un mismo corte anual?",
        dims="Perfil (sexo, edad) · Causa · Geografía (país) · Tiempo (corte anual)", medidas="Personas desplazadas al cierre del año (SADD)",
        jerarquias="Perfil: ciclo de vida → grupo de edad · Geografía: ámbito → país",
        profundiza="La etapa 4 mostró el perfil por sexo y edad en total; aquí se cruza con la causa y el país para ver dónde el perfil es distinto del promedio mundial.",
        seleccion=[sel_item("Causa", "Causa", causa), sel_item("Año (corte)", "Tiempo", anio), sel_item("País", "Geografía", pais),
                   {"filtro": "Nivel de edad", "dimension": "Perfil", "valor": NIVELES[nivel][1], "activo": True}],
        filtros=[{"name": "causa", "label": "Causa", "dim": "Causa", "value": causa, "opts": [("", "Ambas")] + [(c, c) for c in olap.ORDEN_FIJO["causa"]]},
                 {"name": "anio", "label": "Año de corte", "dim": "Tiempo", "value": anio,
                  "opts": [(p, p) for p in olap.orden_valores("periodo", valores("periodo", {"fuente_corta": ["SADD"]}))][::-1]},
                 {"name": "pais", "label": "País", "dim": "Geografía", "value": pais,
                  "opts": [("", "Todos")] + [(p, p) for p in valores("pais", {"fuente_corta": ["SADD"]})]}],
        controles=[{"name": "nivel", "label": "Nivel de Perfil (drill-down / roll-up)", "value": nivel, "opts": [("ciclo_vida", "Ciclo de vida (general)"), ("grupo_edad", "Grupo de edad (detalle)")]},
                   {"name": "cols", "label": "Columnas de la matriz", "value": colsd, "opts": [("causa", "Causa"), ("sexo", "Sexo")]},
                   {"name": "modo", "label": "Valores de la matriz", "value": modo, "opts": [("valor", "Valores absolutos"), ("pct_col", "% de la columna"), ("pct_fila", "% de la fila")]}],
        pivot=pivot, kpis=kpis, charts=[g1, g2], matriz=mat, interpretacion=interp, sql=t.consultas[:6],
        limitacion="El stock es una foto a fin de año: no se suma entre años y no indica cuántas personas se desplazaron durante el año. La desagregación por sexo y edad no está disponible para todos los países ni causas, y solo se incluyen registros con desagregación.",
        decision="Incluir servicios de protección y educación en la planeación de respuesta cuando la proporción de menores supere ampliamente el promedio, y servicios de salud y cuidado para población mayor en los países donde predomine ese grupo.",
        conocimientos=q3_conocimientos())


def q3_conocimientos():
    t = Traza()
    d, _ = agg("stock", ["causa", "ciclo_vida"], {"periodo": ["2024"]}, t)
    pv = d.pivot(index="causa", columns="ciclo_vida", values="valor")
    tot = pv.sum(axis=1)
    pm = {c: pc(pv.loc[c, "Menores de 18"], tot[c]) for c in pv.index}
    k1 = conocimiento(
        "¿La proporción de menores de 18 años entre las personas desplazadas es distinta según la causa en 2024?",
        "Perfil (ciclo de vida) · Causa · medida: personas desplazadas al cierre (SADD, «Ambos sexos»)",
        "Slice del corte 2024; agrupación causa × ciclo de vida; porcentaje con denominador = stock total de cada causa (columna).",
        "Vista 3, matriz ciclo de vida × causa en modo «% de la columna» con año 2024.",
        f"Conflicto: {fmt(tot[CAUSA_C])} personas, de las cuales {fmt(pv.loc[CAUSA_C, 'Menores de 18'])} son menores ({fmt(pm[CAUSA_C], 1)} %). Desastres: {fmt(tot[CAUSA_D])} personas y {fmt(pv.loc[CAUSA_D, 'Menores de 18'])} menores ({fmt(pm[CAUSA_D], 1)} %).",
        f"En ambas causas los menores son cerca de dos de cada cinco desplazados, un poco más en desastres ({fmt(pm[CAUSA_D] - pm[CAUSA_C], 1)} puntos porcentuales de diferencia). El dato evidente («muchos menores») se matiza: la diferencia entre causas es moderada.",
        "Da una referencia para dimensionar servicios dirigidos a la infancia en ambos tipos de crisis.",
        "Es una asociación en un corte; no explica por qué cambia el perfil entre causas ni cubre países sin desagregación por edad.", "q3", t.consultas[:2])
    t2 = Traza()
    r, _ = agg("stock", ["pais", "ciclo_vida"], {"periodo": ["2024"]}, t2)
    pv2 = r.pivot(index="pais", columns="ciclo_vida", values="valor").fillna(0)
    pv2["total"] = pv2.sum(axis=1)
    pv2 = pv2[pv2.total >= 500000]
    pv2["pct"] = pv2["Menores de 18"] / pv2["total"] * 100
    alto = pv2.sort_values("pct", ascending=False).head(4)
    bajo = pv2.sort_values("pct").head(3)
    col = pv2.loc["Colombia"] if "Colombia" in pv2.index else None
    k2 = conocimiento(
        "¿Qué países con gran población desplazada tienen un perfil de edad muy distinto al promedio mundial y dónde está Colombia?",
        "Geografía (país) · Perfil (ciclo de vida) · Tiempo (2024) · medida: personas desplazadas (SADD)",
        "Slice 2024; agrupación por país × ciclo de vida; filtro de países con al menos 500.000 desplazados (para evitar porcentajes inestables); orden por % de menores (denominador: stock del país).",
        "Vista 3, gráfico de ranking de % de menores y matriz con filtro de país.",
        f"Entre {len(pv2)} países con ≥ 500.000 desplazados, los mayores % de menores son " + ", ".join(f"{i} ({fmt(v, 1)} %)" for i, v in zip(alto.index, alto['pct'])) + "; los menores son " + ", ".join(f"{i} ({fmt(v, 1)} %)" for i, v in zip(bajo.index, bajo['pct']))
        + (f". Colombia: {fmt(col['pct'], 1)} % de menores sobre {fmt(col['total'])} personas." if col is not None else "."),
        "El perfil promedio mundial esconde diferencias grandes: más de la mitad de los desplazados son menores en algunos países africanos, mientras que en Ucrania y Colombia son una proporción claramente menor.",
        "Permite priorizar programas de infancia (educación, protección) por país y evitar aplicar un perfil promedio.",
        "Son asociaciones; las diferencias pueden reflejar la estructura de edad de la población general de cada país (hipótesis no comprobada, falta normalizar por población).", "q3", t2.consultas[:2])
    return [k1, k2]


# =====================================================================================
# Q4 — Triangulación de fuentes en Colombia (Fuente · Tiempo · Causa · Geografía)
# =====================================================================================
def q4(a):
    t = Traza()
    med = a.get("medida", "flujo")
    causa = a.get("causa", "")
    ventana = a.get("ventana", "")
    nt = a.get("nivel_t", "periodo")
    modo = a.get("modo", "valor")
    pivot = a.get("pivot") == "1"
    ven = [ventana] if ventana else ["2009–2016", "2017–2024"]
    filt = {"pais": ["Colombia"], "ventana": ven}
    if causa:
        filt["causa"] = [causa]
    lab = MEDIDAS[med]["nombre"]
    serie, _ = agg(med, ["periodo", "causa"], filt, t)
    serie = serie[serie["valor"].notna()]
    ys = olap.orden_valores("periodo", serie["periodo"].unique().tolist())
    ds = []
    for cz in olap.ORDEN_FIJO["causa"]:
        if causa and cz != causa:
            continue
        d = serie[serie.causa == cz].set_index("periodo")["valor"]
        if len(d):
            ds.append({"label": cz, "data": [f(d.get(y)) for y in ys], "color": CAUSA_COL[cz]})
    g1 = {"tipo": "line", "titulo": f"Colombia — {lab} por año ({MEDIDAS[med]['fuente']})", "labels": ys, "datasets": ds, "unidad": MEDIDAS[med]["unidad"]}
    # comparación de promedios anuales
    cm, _ = agg("cnmh_anual", ["periodo"], {"pais": ["Colombia"]}, t)
    cmv = cm.sort_values("periodo")
    cm_tot = f(agg("cnmh_anual", [], {"pais": ["Colombia"], "periodo": ["2005-2014"]}, t)[0]["valor"].iloc[0])
    gi = agg("flujo_anual", ["ventana"], {"pais": ["Colombia"], "causa": [CAUSA_C], "ventana": ["2009–2016", "2017–2024"]}, t)[0]
    labs = [f"CNMH {p}" for p in olap.orden_valores("periodo", cmv["periodo"].tolist())]
    vals = [f(cmv.set_index("periodo")["valor"].get(p)) for p in olap.orden_valores("periodo", cmv["periodo"].tolist())]
    for r in gi.sort_values("ventana").itertuples():
        labs.append(f"IDMC {r.ventana}")
        vals.append(f(r.valor))
    g2 = {"tipo": "bar", "horizontal": False, "titulo": "Colombia, conflicto — promedio anual por periodo y fuente (no son series equivalentes)", "labels": labs,
          "datasets": [{"label": "desplazamientos por año", "data": vals, "color": COL["conf"], "colors": [COL["des"]] * len(cmv) + [COL["conf"]] * len(gi)}],
          "unidad": "desplazamientos/año"}
    # indicadores
    gi_c = f(agg("flujo_anual", [], {"pais": ["Colombia"], "causa": [CAUSA_C], "periodo": [str(y) for y in range(2009, 2015)]}, t)[0]["valor"].iloc[0])
    # para el flujo GIDD por año, 'flujo_anual' sobre 6 años de duración 1 → promedio
    cm_ult = serie["valor"].tolist()
    ultimo_y = ys[-1] if ys else "—"
    ult = serie[serie.periodo == ultimo_y]["valor"].sum() if ys else None
    prom = serie.groupby("periodo")["valor"].sum().mean() if ys else None
    kpis = [
        {"titulo": f"Último año de la selección ({ultimo_y})", "valor": fmt(f(ult)), "unidad": f"{MEDIDAS[med]['unidad']} · {MEDIDAS[med]['fuente']}",
         "nota": "Valor del último año seleccionado; para stock es la foto a fin de año."},
        {"titulo": "Promedio anual de la selección", "valor": fmt(f(prom)), "unidad": f"{MEDIDAS[med]['unidad']} por año (promedio de {len(ys)} años)",
         "nota": "Promedio de los totales anuales; para stock es un promedio de cortes, no una suma."},
        {"titulo": "CNMH 2005-2014 ÷ IDMC 2009–2014", "valor": fmt(cm_tot / gi_c, 2) if gi_c else "—", "unidad": f"razón de promedios anuales ({fmt(cm_tot)} ÷ {fmt(gi_c)})",
         "nota": "Razón de dos promedios por año; no se interpreta como error: las fuentes miden cosas distintas."},
    ]
    mat = matriz_ui(med, nt if nt in ("ventana", "periodo") else "periodo", "causa", filt, modo, pivot, None, t)
    interp = (f"La fuente activa es {MEDIDAS[med]['fuente']} ({lab}). En la selección ({causa or 'ambas causas'}; {ventana or '2009–2024'}) el promedio anual es {fmt(f(prom))} {MEDIDAS[med]['unidad']}. "
              f"El CNMH registra {fmt(cm_tot)} desplazamientos por año en 2005-2014 frente a {fmt(gi_c)} por año de IDMC en 2009–2014 (razón {fmt(cm_tot / gi_c, 2)}): "
              "magnitudes del mismo orden, pero que no deben sumarse ni compararse como idénticas.")
    return dict(
        id="q4", titulo="Triangulación de fuentes: ¿qué tan consistentes son las mediciones sobre Colombia?",
        pregunta="¿Cómo se comparan, por año y causa, las tres formas de medir el desplazamiento en Colombia (flujo anual IDMC, stock IDMC y registro acumulado del CNMH) y qué tan comparables son?",
        dims="Fuente (institución → fuente) · Tiempo · Causa · Geografía (Colombia)", medidas="Nuevos desplazamientos; personas desplazadas al cierre; registrados por año (CNMH)",
        jerarquias="Fuente: institución → fuente · Tiempo: ventana → año",
        profundiza="La etapa 4 ya mostraba que el CNMH y el IDMC miden distinto; aquí se cuantifica la diferencia por años equivalentes y se muestra qué nivel de cada serie puede compararse.",
        seleccion=[sel_item("Fuente / medida", "Fuente", f"{MEDIDAS[med]['fuente']} · {lab}"), sel_item("Causa", "Causa", causa),
                   sel_item("Ventana", "Tiempo", ventana or "2009–2016 y 2017–2024"), {"filtro": "País", "dimension": "Geografía", "valor": "Colombia", "activo": True}],
        filtros=[{"name": "medida", "label": "Fuente / medida (slice de Fuente)", "dim": "Fuente", "value": med,
                  "opts": [("flujo", "IDMC GIDD — flujo anual"), ("stock_gidd", "IDMC GIDD — stock reportado"), ("stock", "IDMC SADD — stock a fin de año")]},
                 {"name": "causa", "label": "Causa", "dim": "Causa", "value": causa, "opts": [("", "Ambas")] + [(c, c) for c in olap.ORDEN_FIJO["causa"]]},
                 {"name": "ventana", "label": "Ventana de tiempo", "dim": "Tiempo", "value": ventana, "opts": [("", "Ambas")] + [(v, v) for v in ("2009–2016", "2017–2024")]}],
        controles=[{"name": "nivel_t", "label": "Nivel de Tiempo (drill-down / roll-up)", "value": nt, "opts": [("ventana", "Ventana (general)"), ("periodo", "Año (detalle)")]},
                   {"name": "modo", "label": "Valores de la matriz", "value": modo, "opts": [("valor", "Valores absolutos"), ("pct_col", "% de la columna"), ("pct_fila", "% de la fila")]}],
        pivot=pivot, kpis=kpis, charts=[g1, g2], matriz=mat, interpretacion=interp, sql=t.consultas[:6],
        limitacion="Las tres medidas no son equivalentes: el flujo cuenta desplazamientos nuevos del año, el stock cuenta personas desplazadas al cierre y el CNMH cuenta registros acumulados por periodo. Los periodos solo se solapan parcialmente (2009–2014) y no se pueden sumar entre fuentes.",
        decision="Usar el CNMH para la dimensión histórica y territorial (1980–2014) y el IDMC para el seguimiento reciente (2009–2024), reportando siempre la fuente y el tipo de medida, y no combinar sus cifras en un solo total.",
        conocimientos=q4_conocimientos())


def q4_conocimientos():
    t = Traza()
    cm = f(agg("cnmh_anual", [], {"pais": ["Colombia"], "periodo": ["2005-2014"]}, t)[0]["valor"].iloc[0])
    gi = f(agg("flujo_anual", [], {"pais": ["Colombia"], "causa": [CAUSA_C], "periodo": [str(y) for y in range(2009, 2015)]}, t)[0]["valor"].iloc[0])
    sd = f(agg("stock", [], {"pais": ["Colombia"], "causa": [CAUSA_C], "periodo": ["2024"]}, t)[0]["valor"].iloc[0])
    k1 = conocimiento(
        "¿Cuántos desplazamientos por año reportan el CNMH y el IDMC para Colombia en periodos equivalentes?",
        "Fuente (CNMH, GIDD) · Tiempo (2005–2014 vs 2009–2014) · Causa (conflicto) · Geografía (Colombia); medida: desplazamientos por año",
        "Dice: país = Colombia, causa = conflicto y fuente; el CNMH se normaliza dividiendo el total del periodo 2005-2014 entre sus 10 años; el IDMC se promedia sobre los 6 años 2009–2014 (2008 no tiene datos de conflicto).",
        "Vista 4, indicador «CNMH ÷ IDMC» y gráfico de promedios anuales.",
        f"CNMH 2005-2014: {fmt(cm)} desplazamientos/año. IDMC 2009–2014: {fmt(gi)} desplazamientos/año. Razón CNMH/IDMC = {fmt(cm / gi, 2)}.",
        "Las dos fuentes coinciden en el orden de magnitud (cientos de miles por año) pero no en el valor: el CNMH reconstruye hechos de forma acumulada y el IDMC reporta flujos anuales. La diferencia muestra que no son intercambiables.",
        "Indica que cualquier análisis que mezcle ambas fuentes debe estar normalizado por año y etiquetado con su fuente.",
        "Los periodos no coinciden exactamente (10 vs 6 años) y las definiciones difieren; la razón no mide error de ninguna fuente.", "q4", t.consultas[:3])
    t2 = Traza()
    s, _ = agg("flujo", ["periodo"], {"pais": ["Colombia"], "causa": [CAUSA_C], "periodo": [str(y) for y in range(2009, 2025)]}, t2)
    s = s.set_index("periodo")["valor"]
    a1 = s.loc[[str(y) for y in range(2009, 2022)]].mean()
    a2 = s.loc[["2022", "2023", "2024"]].mean()
    mx = s.idxmax()
    k2 = conocimiento(
        "¿Cambió el nivel anual de nuevos desplazamientos por conflicto en Colombia en los últimos años y cómo se relaciona con el stock?",
        "Tiempo (año) · Causa (conflicto) · Fuente (GIDD flujo y SADD stock) · Geografía (Colombia)",
        "Slice país = Colombia y causa = conflicto; drill-down de ventana a año; promedios de los totales anuales de 2009–2021 y 2022–2024 (promedios calculados sobre las sumas anuales, no sobre porcentajes); consulta del stock SADD 2024.",
        "Vista 4, gráfico de línea del flujo anual y matriz año × causa.",
        f"Promedio anual 2009–2021: {fmt(a1)} desplazamientos; 2022–2024: {fmt(a2)} (×{fmt(a2 / a1, 2)}). Año máximo: {mx} con {fmt(s.max())}. El stock SADD de conflicto al cierre de 2024 es {fmt(sd)} personas.",
        "Desde 2022 el flujo anual reportado se multiplica respecto del periodo anterior, pero el stock no se reconstruye sumando flujos: el stock es una medida distinta (personas que siguen desplazadas), por lo que ambos indicadores se leen por separado.",
        "Ayuda a identificar un cambio de nivel reciente que justifica revisar la capacidad de respuesta en Colombia.",
        "El aumento es una asociación descriptiva de datos reportados; no prueba causa y puede mezclar mejoras en la captura de datos con cambios reales.", "q4", t2.consultas[:3])
    return [k1, k2]


VISTAS = {"q1": q1, "q2": q2, "q3": q3, "q4": q4}


# =====================================================================================
# Material de la página de entrada: modelo, operaciones con ejemplo real, conocimientos
# =====================================================================================
MODELO = {
    "hecho": {
        "nombre": "hechos_desplazamiento",
        "proposito": "Registrar, para cada fuente, lugar, periodo, causa y perfil, la cantidad de personas o desplazamientos reportados.",
        "granularidad": "Un registro por combinación única de (periodo × geografía × causa × perfil × fuente). Es equivalente a una fila del dataset tratado: 28.122 registros. La unidad de análisis es la «cifra reportada de desplazamiento»; la granularidad es el detalle con que se almacena.",
    },
    "dimensiones": [
        ("dim_tiempo", "tiempo_key (PK)", "periodo, anio_inicio, anio_fin, duracion_anios, ventana, decada", "ventana → periodo (año o periodo CNMH)"),
        ("dim_geografia", "geo_key (PK)", "ambito, nivel, iso3, pais, departamento, municipio", "ámbito → país → departamento → municipio"),
        ("dim_causa", "causa_key (PK)", "causa", "—"),
        ("dim_perfil", "perfil_key (PK)", "sexo, grupo_edad, ciclo_vida, orden_edad", "ciclo de vida → grupo de edad"),
        ("dim_fuente", "fuente_key (PK)", "fuente_corta, fuente_nombre, institucion, tipo_medida, tipo_fuente", "institución → fuente"),
    ],
    "medidas": [
        ("Nuevos desplazamientos", "SUM(personas_desplazadas) con fuente = GIDD", "desplazamientos", "Aditiva en todas las dimensiones (flujo anual). No equivale a personas únicas."),
        ("Personas desplazadas al cierre", "SUM(personas_desplazadas) con fuente = SADD, «Ambos sexos», un solo año", "personas", "Aditiva en geografía, causa y perfil; NO aditiva en el tiempo (se fija un corte)."),
        ("Registrados CNMH por año", "SUM(personas_desplazadas) ÷ Σ duracion_anios de los periodos incluidos (fuente = CNMH)", "desplazamientos/año", "Es una razón: se recalcula en cada nivel; no se suman ni promedian valores ya normalizados."),
        ("Participación (%)", "valor del grupo ÷ valor del denominador indicado × 100", "%", "No aditiva: se recalcula siempre con el denominador explícito."),
        ("Stock reportado GIDD", "SUM(desplazamiento_stock) con fuente = GIDD", "personas", "No aditiva en el tiempo; con muchos valores nulos (no reportado ≠ 0)."),
    ],
}


def operaciones():
    out = []
    t = Traza()
    # drill-down
    d0, _ = agg("cnmh", ["departamento"], {"departamento": ["Antioquia"]}, t)
    m0, _ = agg("cnmh", ["municipio"], {"departamento": ["Antioquia"]}, t)
    m0 = m0.sort_values("valor", ascending=False)
    out.append(dict(op="Drill-down", vista="q2", params="nivel=municipio&depto=Antioquia",
        dims="Geografía (departamento → municipio) · medida: desplazados registrados (CNMH)",
        filtros="Departamento = Antioquia; nivel municipio",
        proc="GROUP BY departamento → GROUP BY municipio WHERE departamento = 'Antioquia'.",
        resultado=f"Antioquia suma {fmt(d0['valor'].iloc[0])}. Al bajar a municipio la suma de los {len(m0)} municipios es {fmt(m0['valor'].sum())} (igual) y el primero es {m0.iloc[0]['municipio']} con {fmt(m0.iloc[0]['valor'])} ({fmt(pc(m0.iloc[0]['valor'], m0['valor'].sum()), 1)} %). El porcentaje se recalcula con el total de Antioquia como denominador.",
        sql=t.consultas[-1]))
    t = Traza()
    ya, _ = agg("flujo", ["periodo"], {"ventana": ["2017–2024"], "causa": [CAUSA_C]}, t)
    vv, _ = agg("flujo", ["ventana"], {"ventana": ["2017–2024"], "causa": [CAUSA_C]}, t)
    out.append(dict(op="Roll-up", vista="q1", params="nivel_t=ventana&causa=" + CAUSA_C,
        dims="Tiempo (año → ventana) · Causa · medida: nuevos desplazamientos (GIDD)", filtros="Causa = conflicto; ventana 2017–2024",
        proc="GROUP BY periodo (8 años) → GROUP BY ventana (1 grupo).",
        resultado=f"La suma de los 8 valores anuales ({fmt(ya['valor'].sum())}) coincide con el valor de la ventana ({fmt(vv['valor'].iloc[0])}): el roll-up recalcula la medida desde el nivel detallado, no promedia ni suma valores ya agregados.",
        sql=t.consultas[-1]))
    t = Traza()
    sl = f(agg("stock", [], {"periodo": ["2024"]}, t)[0]["valor"].iloc[0])
    out.append(dict(op="Slice", vista="q3", params="anio=2024",
        dims="Tiempo (año) · medida: personas desplazadas al cierre (SADD)", filtros="Año = 2024 (un valor de la dimensión Tiempo)",
        proc="WHERE periodo = '2024' AND fuente = 'SADD' AND sexo = 'Ambos sexos'.",
        resultado=f"Fijar el corte 2024 produce {fmt(sl)} personas desplazadas internas, igual al valor de la etapa 4. Sin el slice el stock no podría sumarse entre años.",
        sql=t.consultas[-1]))
    t = Traza()
    dc = f(agg("cnmh", [], {"periodo": ["1989-1996"], "departamento": ["Antioquia"]}, t)[0]["valor"].iloc[0])
    tt = f(agg("cnmh", [], {"periodo": ["1989-1996"]}, t)[0]["valor"].iloc[0])
    out.append(dict(op="Dice", vista="q2", params="periodo=1989-1996&depto=Antioquia",
        dims="Tiempo (periodo) × Geografía (departamento) · medida: desplazados registrados (CNMH)", filtros="Periodo = 1989-1996 Y departamento = Antioquia",
        proc="WHERE periodo = '1989-1996' AND departamento = 'Antioquia' (dos dimensiones a la vez).",
        resultado=f"El subcubo contiene {fmt(dc)} registros, {fmt(pc(dc, tt), 1)} % del total nacional del periodo ({fmt(tt)}); el denominador del porcentaje es el total nacional del mismo periodo.",
        sql=t.consultas[0]))
    t = Traza()
    m1 = matriz_ui("flujo", "pais", "causa", {"ventana": ["2017–2024"]}, "valor", False, 5, t)
    m2 = matriz_ui("flujo", "pais", "causa", {"ventana": ["2017–2024"]}, "valor", True, 5, t)
    out.append(dict(op="Pivot", vista="q1", params="pivot=1&nivel_g=pais",
        dims="Geografía (país) × Causa · medida: nuevos desplazamientos (GIDD)", filtros="Ventana 2017–2024; el botón «Pivotar» intercambia filas y columnas",
        proc="La misma consulta GROUP BY pais, causa se dispone como países en filas y causas en columnas, o al revés.",
        resultado=f"Antes: filas = {m1['filas']}, columnas = {m1['columnas']}; después: filas = {m2['filas']}, columnas = {m2['columnas']}. El total general ({fmt(m1['total'])}) no cambia, solo la disposición; con porcentajes, el denominador pasa de la columna a la fila.",
        sql=t.consultas[0]))
    return out


def resumen_conocimientos():
    items = []
    for k, fn in (("q1", q1_conocimientos), ("q2", q2_conocimientos), ("q3", q3_conocimientos), ("q4", q4_conocimientos)):
        for i, c in enumerate(fn(), 1):
            items.append((k, i, c))
    return items
