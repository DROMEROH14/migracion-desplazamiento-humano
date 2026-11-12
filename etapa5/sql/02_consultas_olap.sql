-- Etapa 5 · Consultas OLAP sobre el modelo estrella (SQLite). Cada bloque indica la operación y la vista de Flask que la usa.
-- Todas consultan la vista vw_hechos (hecho + 5 dimensiones). Cuando la medida es stock (SADD) se fija un solo año y «Ambos sexos».

-- [DRILL-DOWN] Vista 2: de departamento a municipio (Antioquia, CNMH)
SELECT departamento, SUM(personas_desplazadas) AS desplazados
FROM vw_hechos WHERE fuente_corta='CNMH' AND departamento='Antioquia' GROUP BY departamento;
SELECT municipio, SUM(personas_desplazadas) AS desplazados
FROM vw_hechos WHERE fuente_corta='CNMH' AND departamento='Antioquia'
GROUP BY municipio ORDER BY desplazados DESC;

-- [ROLL-UP] Vista 1: de año a ventana (conflicto, 2017–2024)
SELECT periodo, SUM(personas_desplazadas) AS nuevos_desplazamientos
FROM vw_hechos WHERE fuente_corta='GIDD' AND causa='Conflicto armado / violencia' AND ventana='2017–2024'
GROUP BY periodo ORDER BY periodo;
SELECT ventana, SUM(personas_desplazadas) AS nuevos_desplazamientos
FROM vw_hechos WHERE fuente_corta='GIDD' AND causa='Conflicto armado / violencia' AND ventana='2017–2024'
GROUP BY ventana;

-- [SLICE] Vista 3: un valor de Tiempo (corte 2024) para el stock SADD
SELECT SUM(personas_desplazadas) AS personas_desplazadas_2024
FROM vw_hechos WHERE fuente_corta='SADD' AND sexo='Ambos sexos' AND periodo='2024';

-- [DICE] Vista 2: periodo 1989-1996 Y departamento Antioquia, con % sobre el total nacional del periodo
SELECT SUM(CASE WHEN departamento='Antioquia' THEN personas_desplazadas END) AS antioquia,
       SUM(personas_desplazadas) AS total_periodo,
       100.0*SUM(CASE WHEN departamento='Antioquia' THEN personas_desplazadas END)/SUM(personas_desplazadas) AS pct
FROM vw_hechos WHERE fuente_corta='CNMH' AND periodo='1989-1996';

-- [PIVOT] Vista 1: países × causa (2017–2024) -- el pivot intercambia filas y columnas
SELECT pais,
       SUM(CASE WHEN causa='Conflicto armado / violencia' THEN personas_desplazadas END) AS conflicto,
       SUM(CASE WHEN causa='Desastre natural / climático' THEN personas_desplazadas END) AS desastres,
       SUM(personas_desplazadas) AS total
FROM vw_hechos WHERE fuente_corta='GIDD' AND ventana='2017–2024' GROUP BY pais ORDER BY total DESC LIMIT 10;
SELECT causa,
       SUM(CASE WHEN pais='Philippines' THEN personas_desplazadas END) AS philippines,
       SUM(CASE WHEN pais='China' THEN personas_desplazadas END) AS china,
       SUM(CASE WHEN pais='India' THEN personas_desplazadas END) AS india
FROM vw_hechos WHERE fuente_corta='GIDD' AND ventana='2017–2024' GROUP BY causa;

-- [VISTA 1] participación del conflicto por ventana (denominador: conflicto + desastres de la ventana)
SELECT ventana,
       SUM(CASE WHEN causa='Conflicto armado / violencia' THEN personas_desplazadas END) AS conflicto,
       SUM(personas_desplazadas) AS total,
       100.0*SUM(CASE WHEN causa='Conflicto armado / violencia' THEN personas_desplazadas END)/SUM(personas_desplazadas) AS pct_conflicto
FROM vw_hechos WHERE fuente_corta='GIDD' AND ventana IN ('2009–2016','2017–2024') GROUP BY ventana;

-- [VISTA 2] participación departamental por periodo (denominador: total nacional del periodo)
SELECT d.departamento, d.periodo, 100.0*d.v/t.v AS pct
FROM (SELECT departamento, periodo, SUM(personas_desplazadas) v FROM vw_hechos WHERE fuente_corta='CNMH' GROUP BY 1,2) d
JOIN (SELECT periodo, SUM(personas_desplazadas) v FROM vw_hechos WHERE fuente_corta='CNMH' GROUP BY 1) t USING (periodo)
WHERE d.departamento IN ('Antioquia','Córdoba','Nariño','Valle Del Cauca') ORDER BY d.departamento, d.periodo;

-- [VISTA 2] medida por año = total ÷ Σ años de los periodos (razón, se recalcula en cada nivel)
SELECT periodo, SUM(personas_desplazadas)*1.0/MAX(duracion_anios) AS desplazados_por_anio
FROM vw_hechos WHERE fuente_corta='CNMH' GROUP BY periodo ORDER BY MIN(anio_inicio);

-- [VISTA 3] % de menores de 18 por causa, corte 2024 (denominador: stock de la causa)
SELECT causa,
       100.0*SUM(CASE WHEN ciclo_vida='Menores de 18' THEN personas_desplazadas END)/SUM(personas_desplazadas) AS pct_menores
FROM vw_hechos WHERE fuente_corta='SADD' AND sexo='Ambos sexos' AND periodo='2024' GROUP BY causa;

-- [VISTA 3] países con ≥ 500.000 desplazados, ordenados por % de menores
SELECT pais, SUM(personas_desplazadas) AS total,
       100.0*SUM(CASE WHEN ciclo_vida='Menores de 18' THEN personas_desplazadas END)/SUM(personas_desplazadas) AS pct_menores
FROM vw_hechos WHERE fuente_corta='SADD' AND sexo='Ambos sexos' AND periodo='2024'
GROUP BY pais HAVING total>=500000 ORDER BY pct_menores DESC;

-- [VISTA 4] Colombia, conflicto: CNMH 2005-2014 por año vs IDMC 2009–2014 por año
SELECT 'CNMH 2005-2014' AS fuente, SUM(personas_desplazadas)*1.0/10 AS por_anio
FROM vw_hechos WHERE fuente_corta='CNMH' AND periodo='2005-2014'
UNION ALL
SELECT 'IDMC 2009-2014', SUM(personas_desplazadas)*1.0/6
FROM vw_hechos WHERE fuente_corta='GIDD' AND pais='Colombia' AND causa='Conflicto armado / violencia' AND periodo BETWEEN '2009' AND '2014';
