# Etapa 5 · Diccionario del modelo estrella y mapeo desde el dataset tratado

Origen: `data/dataset_tratado_etapa3.csv` (28.122 registros, resultado de la Etapa 3).
Destino: `data/estrella.db` (SQLite) creada con `etapa5/sql/01_crear_esquema_estrella.sql` y cargada por `etapa5/etl_estrella.py`.
Diagrama: `etapa5/diagrama_modelo_estrella.svg` / `.png`.

## Granularidad
Un registro de `hechos_desplazamiento` = una combinación única de **periodo × geografía × causa × perfil × fuente** (restricción `UNIQUE` sobre las cinco claves foráneas). Es la misma granularidad del dataset tratado (una fila por cifra reportada), por lo que el modelo tiene 28.122 hechos.
La **unidad de análisis** es la cifra reportada de desplazamiento; no es una persona única.

## Tablas
| Tabla | Clave | Campos | Origen (columna del dataset tratado) | Transformación |
|---|---|---|---|---|
| dim_tiempo | tiempo_key (PK) | periodo, anio_inicio, anio_fin, duracion_anios, ventana, decada | `periodo`, `anio`, `duracion_periodo_anios` | anio_fin = anio + duración − 1; ventana: «Antes de 2009», «2009–2016», «2017–2024» (IDMC) o «CNMH 1980–2014»; década derivada |
| dim_geografia | geo_key (PK) | ambito, nivel, iso3, pais, departamento, municipio | `nivel`, `iso3`, `pais`, `departamento`, `municipio` | Nulos → «No aplica» (categoría explícita); ámbito = «Colombia» o «Resto del mundo» |
| dim_causa | causa_key (PK) | causa | `causa` | Valores distintos |
| dim_perfil | perfil_key (PK) | sexo, grupo_edad, ciclo_vida, orden_edad | `sexo`, `grupo_edad` | Female/Male/Both sexes → Mujeres/Hombres/Ambos sexos; «Todos» → «No desagregado»; ciclo_vida: 0-4, 5-11, 12-17 → Menores de 18; 18-59 → Adultos; 60+ → Mayores |
| dim_fuente | fuente_key (PK) | fuente_corta, fuente_nombre, institucion, tipo_medida, tipo_fuente | `fuente`, `tipo_fuente` | fuente_corta (GIDD/SADD/CNMH) extraída del nombre; institución y tipo de medida (flujo anual, stock a fin de año, acumulado por periodo) |
| hechos_desplazamiento | hecho_key (PK); 5 FK | personas_desplazadas, desplazamiento_stock, duracion_anios, personas_por_anio, es_outlier, id_origen, clave_negocio | `personas_desplazadas`, `desplazamiento_stock`, `duracion_periodo_anios`, `outlier_iqr_extremo`, `id`, `clave_negocio` | personas_por_anio = personas_desplazadas ÷ duración; `id_origen` y `clave_negocio` UNIQUE para trazabilidad |
| vw_hechos | — | vista desnormalizada (hecho + 5 dimensiones) | — | Solo joins N:1 por clave sustituta: no multiplica filas |

## Jerarquías
- Tiempo: ventana → periodo (año, o periodo CNMH).
- Geografía: ámbito → país → departamento → municipio.
- Perfil: ciclo de vida → grupo de edad.
- Fuente: institución → fuente.

## Medidas
| Medida | Fórmula | Unidad | Agregación |
|---|---|---|---|
| Nuevos desplazamientos | SUM(personas_desplazadas), fuente = GIDD | desplazamientos | Suma en todas las dimensiones |
| Personas desplazadas al cierre | SUM(personas_desplazadas), fuente = SADD, «Ambos sexos», un solo año | personas | Suma en geografía/causa/perfil; **no** en el tiempo |
| Registrados CNMH por año | SUM(personas_desplazadas) ÷ Σ duración de los periodos | desplazamientos/año | Razón recalculada en cada nivel |
| Participación (%) | grupo ÷ denominador indicado × 100 | % | No aditiva; denominador explícito |
| Stock GIDD | SUM(desplazamiento_stock), fuente = GIDD | personas | No aditiva en el tiempo; NULL = no reportado |

## Valores faltantes y categorías desconocidas
- `desplazamiento_stock` NULL = no reportado (no se convierte en cero).
- «No aplica» (geografía) y «No desagregado» (sexo/edad) son categorías explícitas, distintas de NULL y de cero.
- No hay valores negativos en `personas_desplazadas` (restricción CHECK ≥ 0).
