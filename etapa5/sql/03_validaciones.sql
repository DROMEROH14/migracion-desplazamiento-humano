-- Etapa 5 · Validaciones del modelo (cada consulta debe devolver 0 filas / 0 salvo que se indique)
-- 1) Unicidad de claves de las dimensiones
SELECT COUNT(*)-COUNT(DISTINCT tiempo_key) FROM dim_tiempo;
SELECT COUNT(*)-COUNT(DISTINCT geo_key) FROM dim_geografia;
SELECT COUNT(*)-COUNT(DISTINCT causa_key) FROM dim_causa;
SELECT COUNT(*)-COUNT(DISTINCT perfil_key) FROM dim_perfil;
SELECT COUNT(*)-COUNT(DISTINCT fuente_key) FROM dim_fuente;
-- 2) Claves foráneas huérfanas
SELECT COUNT(*) FROM hechos_desplazamiento h LEFT JOIN dim_tiempo d ON d.tiempo_key=h.tiempo_key WHERE d.tiempo_key IS NULL;
SELECT COUNT(*) FROM hechos_desplazamiento h LEFT JOIN dim_geografia d ON d.geo_key=h.geo_key WHERE d.geo_key IS NULL;
SELECT COUNT(*) FROM hechos_desplazamiento h LEFT JOIN dim_causa d ON d.causa_key=h.causa_key WHERE d.causa_key IS NULL;
SELECT COUNT(*) FROM hechos_desplazamiento h LEFT JOIN dim_perfil d ON d.perfil_key=h.perfil_key WHERE d.perfil_key IS NULL;
SELECT COUNT(*) FROM hechos_desplazamiento h LEFT JOIN dim_fuente d ON d.fuente_key=h.fuente_key WHERE d.fuente_key IS NULL;
-- 3) Duplicados en la granularidad
SELECT tiempo_key,geo_key,causa_key,perfil_key,fuente_key,COUNT(*) FROM hechos_desplazamiento GROUP BY 1,2,3,4,5 HAVING COUNT(*)>1;
-- 4) Conteo de registros (debe ser 28122) y suma por fuente
SELECT COUNT(*) FROM hechos_desplazamiento;
SELECT fuente_corta, COUNT(*), SUM(personas_desplazadas) FROM vw_hechos GROUP BY fuente_corta;
-- 5) El join de la vista no multiplica filas (debe ser igual al conteo anterior)
SELECT COUNT(*) FROM vw_hechos;
-- 6) Valores faltantes / desconocidos (NULL = no reportado, y las categorías explícitas son No aplica y No desagregado)
SELECT COUNT(*) FROM hechos_desplazamiento WHERE desplazamiento_stock IS NULL;
SELECT COUNT(*) FROM dim_perfil p JOIN hechos_desplazamiento h USING (perfil_key) WHERE p.sexo='No desagregado';
SELECT COUNT(*) FROM hechos_desplazamiento WHERE personas_desplazadas<0;
-- 7) «Ambos sexos» = Mujeres + Hombres (SADD 2024)
SELECT SUM(CASE WHEN sexo='Ambos sexos' THEN personas_desplazadas END) AS ambos,
       SUM(CASE WHEN sexo IN ('Mujeres','Hombres') THEN personas_desplazadas END) AS mujeres_mas_hombres
FROM vw_hechos WHERE fuente_corta='SADD' AND periodo='2024';
