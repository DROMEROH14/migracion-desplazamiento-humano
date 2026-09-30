/* =============================================================
   03_destino_y_rechazos.sql
   Tabla destino (dato ya tratado, listo para usarse) y tabla de
   revisión (registros que no pasaron alguna regla, con el valor
   original conservado y el motivo del rechazo).

   La llave para detectar duplicados/repetir cargas es
   clave_negocio (texto plano construido concatenando las columnas
   que identifican un hecho único: nivel+iso3+departamento+
   municipio+anio+causa+sexo+grupo_edad+fuente), NO el id
   autogenerado del CSV. Se probó primero con HASHBYTES, pero el
   proveedor OLE DB usado en el Data Flow no logró preparar ese
   comando parametrizado de forma confiable, así que se optó por
   la llave en texto plano (NVARCHAR), que es más simple y igual
   de efectiva para este volumen de datos.
   Esa llave tiene un índice UNIQUE, así que un INSERT directo
   con una llave repetida fallaría: por eso la carga real se hace
   siempre con MERGE (ver 05_merge_upsert.sql), que es lo que
   garantiza la idempotencia.
   ============================================================= */

USE MigracionDesplazamiento;
GO

IF OBJECT_ID('etl.desplazamiento_tratado') IS NOT NULL
    DROP TABLE etl.desplazamiento_tratado;
GO

CREATE TABLE etl.desplazamiento_tratado (
    desplazamiento_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
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
    outlier_iqr_extremo      BIT             NOT NULL DEFAULT 0,
    batch_id_origen          INT             NOT NULL,
    batch_id_ultima_actualizacion INT        NOT NULL,
    fecha_carga              DATETIME2       NOT NULL DEFAULT SYSDATETIME(),
    fecha_actualizacion      DATETIME2       NOT NULL DEFAULT SYSDATETIME()
);
GO

CREATE UNIQUE INDEX UX_destino_clave_negocio
    ON etl.desplazamiento_tratado(clave_negocio);
GO

IF OBJECT_ID('etl.desplazamiento_revision') IS NOT NULL
    DROP TABLE etl.desplazamiento_revision;
GO

CREATE TABLE etl.desplazamiento_revision (
    revision_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    clave_negocio     NVARCHAR(600)   NOT NULL,
    motivo_revision   NVARCHAR(60)    NOT NULL,
    -- columnas originales, SIN transformar, para que quien revise
    -- vea exactamente el dato tal como llegó:
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
    fuente_original           NVARCHAR(250)   NULL,
    batch_id                  INT             NOT NULL,
    fecha_deteccion           DATETIME2       NOT NULL DEFAULT SYSDATETIME(),
    resuelto                  BIT             NOT NULL DEFAULT 0,
    fecha_resolucion          DATETIME2       NULL,
    comentario_resolucion     NVARCHAR(400)   NULL
);
GO

CREATE INDEX IX_revision_clave ON etl.desplazamiento_revision(clave_negocio);
GO
