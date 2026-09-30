/* =============================================================
   04_tablas_temporales_lote.sql
   Tablas "de trabajo" de un solo lote: el Data Flow de SSIS
   escribe aquí (después de Derived Column + Data Conversion +
   Lookup + Conditional Split), YA con los tipos correctos y ya
   separados en válidos vs. revisión. Se truncan al inicio de
   cada ejecución del paquete (Execute SQL Task en el Control
   Flow, antes del Data Flow Task).

   El paso de "tmp -> tabla definitiva" lo hace el MERGE
   (05_merge_upsert.sql), no el propio Data Flow. Ese es el punto
   clave que garantiza la idempotencia.
   ============================================================= */

USE MigracionDesplazamiento;
GO

IF OBJECT_ID('etl.tmp_candidatos_validos') IS NOT NULL DROP TABLE etl.tmp_candidatos_validos;
CREATE TABLE etl.tmp_candidatos_validos (
    clave_negocio           NVARCHAR(600)   NOT NULL,
    nivel                   NVARCHAR(20)    NOT NULL,
    iso3                    NVARCHAR(10)    NULL,
    pais                    NVARCHAR(150)   NULL,
    departamento            NVARCHAR(150)   NULL,
    municipio               NVARCHAR(150)   NULL,
    anio                    INT             NOT NULL,
    periodo                  NVARCHAR(20)    NULL,
    causa                   NVARCHAR(60)    NOT NULL,
    sexo                    NVARCHAR(20)    NOT NULL,
    grupo_edad               NVARCHAR(20)    NOT NULL,
    personas_desplazadas     DECIMAL(18,2)   NOT NULL,
    desplazamiento_stock     DECIMAL(18,2)   NULL,
    duracion_periodo_anios   INT             NULL,
    tipo_fuente              NVARCHAR(20)    NOT NULL,
    fuente                  NVARCHAR(250)   NOT NULL,
    outlier_iqr_extremo      BIT             NOT NULL DEFAULT 0
);
GO

IF OBJECT_ID('etl.tmp_revision_lote') IS NOT NULL DROP TABLE etl.tmp_revision_lote;
CREATE TABLE etl.tmp_revision_lote (
    clave_negocio            NVARCHAR(600)   NOT NULL,
    motivo_revision          NVARCHAR(60)    NOT NULL,
    nivel_original            NVARCHAR(20)    NULL,
    iso3_original             NVARCHAR(10)    NULL,
    pais_original             NVARCHAR(150)   NULL,
    departamento_original     NVARCHAR(150)   NULL,
    municipio_original        NVARCHAR(150)   NULL,
    anio_original             NVARCHAR(20)    NULL,
    causa_original            NVARCHAR(60)    NULL,
    sexo_original             NVARCHAR(20)    NULL,
    grupo_edad_original       NVARCHAR(20)    NULL,
    personas_desplazadas_original NVARCHAR(30) NULL,
    fuente_original           NVARCHAR(250)   NULL
);
GO
