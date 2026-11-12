-- =====================================================================
-- Etapa 5 — Modelo estrella: Migración y Desplazamiento Humano
-- Motor: SQLite 3 (consultable desde Flask sin servidor adicional)
-- Tabla de hechos : hechos_desplazamiento
-- Dimensiones     : dim_tiempo, dim_geografia, dim_causa, dim_perfil, dim_fuente
-- =====================================================================
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS vw_hechos;
DROP TABLE IF EXISTS hechos_desplazamiento;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS dim_geografia;
DROP TABLE IF EXISTS dim_causa;
DROP TABLE IF EXISTS dim_perfil;
DROP TABLE IF EXISTS dim_fuente;

-- Jerarquía: ventana -> periodo (año o periodo CNMH)
CREATE TABLE dim_tiempo (
    tiempo_key      INTEGER PRIMARY KEY,
    periodo         TEXT    NOT NULL UNIQUE,      -- '2024' o '1989-1996'
    anio_inicio     INTEGER NOT NULL,
    anio_fin        INTEGER NOT NULL,
    duracion_anios  INTEGER NOT NULL CHECK (duracion_anios >= 1),
    ventana         TEXT    NOT NULL,             -- 'Antes de 2009' | '2009–2016' | '2017–2024' | 'CNMH 1980–2014'
    decada          TEXT    NOT NULL
);

-- Jerarquía: ámbito -> país -> departamento -> municipio
CREATE TABLE dim_geografia (
    geo_key       INTEGER PRIMARY KEY,
    ambito        TEXT NOT NULL,                  -- 'Colombia' | 'Resto del mundo'
    nivel         TEXT NOT NULL CHECK (nivel IN ('Global','Nacional','Regional')),
    iso3          TEXT NOT NULL,
    pais          TEXT NOT NULL,
    departamento  TEXT NOT NULL,                  -- 'No aplica' fuera del nivel Regional
    municipio     TEXT NOT NULL,                  -- 'No aplica' fuera del nivel Regional
    UNIQUE (nivel, iso3, departamento, municipio)
);

CREATE TABLE dim_causa (
    causa_key  INTEGER PRIMARY KEY,
    causa      TEXT NOT NULL UNIQUE
);

-- Jerarquía: ciclo de vida -> grupo de edad ; atributo: sexo
CREATE TABLE dim_perfil (
    perfil_key   INTEGER PRIMARY KEY,
    sexo         TEXT NOT NULL,                   -- 'Mujeres' | 'Hombres' | 'Ambos sexos' | 'No desagregado'
    grupo_edad   TEXT NOT NULL,                   -- '0-4','5-11','12-17','18-59','60+','No desagregado'
    ciclo_vida   TEXT NOT NULL,                   -- 'Menores de 18' | 'Adultos 18–59' | 'Mayores de 60' | 'No desagregado'
    orden_edad   INTEGER NOT NULL,
    UNIQUE (sexo, grupo_edad)
);

-- Jerarquía: institución -> fuente ; atributo: tipo_medida (semántica de la medida)
CREATE TABLE dim_fuente (
    fuente_key    INTEGER PRIMARY KEY,
    fuente_corta  TEXT NOT NULL UNIQUE,           -- 'GIDD' | 'SADD' | 'CNMH'
    fuente_nombre TEXT NOT NULL,
    institucion   TEXT NOT NULL,                  -- 'IDMC' | 'CNMH'
    tipo_medida   TEXT NOT NULL,                  -- 'Flujo anual' | 'Stock a fin de año' | 'Acumulado por periodo'
    tipo_fuente   TEXT NOT NULL
);

-- Granularidad: un registro = una cifra reportada por una fuente para una combinación
-- de (lugar, periodo, causa, sexo/edad). Equivale a un registro del dataset tratado.
CREATE TABLE hechos_desplazamiento (
    hecho_key            INTEGER PRIMARY KEY,
    tiempo_key           INTEGER NOT NULL REFERENCES dim_tiempo(tiempo_key),
    geo_key              INTEGER NOT NULL REFERENCES dim_geografia(geo_key),
    causa_key            INTEGER NOT NULL REFERENCES dim_causa(causa_key),
    perfil_key           INTEGER NOT NULL REFERENCES dim_perfil(perfil_key),
    fuente_key           INTEGER NOT NULL REFERENCES dim_fuente(fuente_key),
    id_origen            INTEGER NOT NULL UNIQUE,   -- id del dataset tratado (Etapa 3)
    clave_negocio        TEXT    NOT NULL UNIQUE,
    personas_desplazadas REAL    NOT NULL CHECK (personas_desplazadas >= 0),
    desplazamiento_stock REAL,                      -- NULL = la fuente no lo reportó (no es cero)
    duracion_anios       INTEGER NOT NULL,
    personas_por_anio    REAL    NOT NULL,          -- personas_desplazadas / duracion_anios
    es_outlier           INTEGER NOT NULL DEFAULT 0 CHECK (es_outlier IN (0,1)),
    UNIQUE (tiempo_key, geo_key, causa_key, perfil_key, fuente_key)
);

CREATE INDEX ix_hechos_tiempo  ON hechos_desplazamiento(tiempo_key);
CREATE INDEX ix_hechos_geo     ON hechos_desplazamiento(geo_key);
CREATE INDEX ix_hechos_causa   ON hechos_desplazamiento(causa_key);
CREATE INDEX ix_hechos_perfil  ON hechos_desplazamiento(perfil_key);
CREATE INDEX ix_hechos_fuente  ON hechos_desplazamiento(fuente_key);

-- Vista desnormalizada (el "cubo"): une el hecho con sus cinco dimensiones
CREATE VIEW vw_hechos AS
SELECT f.hecho_key, f.personas_desplazadas, f.desplazamiento_stock, f.duracion_anios,
       f.personas_por_anio, f.es_outlier,
       t.tiempo_key, t.periodo, t.anio_inicio, t.anio_fin, t.ventana, t.decada,
       g.geo_key, g.ambito, g.nivel, g.iso3, g.pais, g.departamento, g.municipio,
       c.causa_key, c.causa,
       p.perfil_key, p.sexo, p.grupo_edad, p.ciclo_vida, p.orden_edad,
       s.fuente_key, s.fuente_corta, s.institucion, s.tipo_medida
FROM hechos_desplazamiento f
JOIN dim_tiempo    t ON t.tiempo_key  = f.tiempo_key
JOIN dim_geografia g ON g.geo_key     = f.geo_key
JOIN dim_causa     c ON c.causa_key   = f.causa_key
JOIN dim_perfil    p ON p.perfil_key  = f.perfil_key
JOIN dim_fuente    s ON s.fuente_key  = f.fuente_key;
