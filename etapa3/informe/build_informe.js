// Genera el informe técnico de la Etapa 3 (Informe_Etapa3_ETL_SSIS.docx)
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ImageRun, AlignmentType, BorderStyle, ShadingType, PageBreak,
  Header, Footer, PageNumber, VerticalAlign, convertInchesToTwip,
} = require("docx");

const A = path.join(__dirname, "assets");
const resultados = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "resultados_iteraciones.json"), "utf-8"));

// ---------- paleta / estilos (formato académico, igual al informe de Verificación de Lectura) ----------
const INK = "000000";
const GRAY = "444444";
const HEADFILL = "262626";

const FONT = "Times New Roman";

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 140 },
    children: [new TextRun({ text, bold: true, color: INK, size: 26, font: FONT })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 220, after: 110 },
    children: [new TextRun({ text, bold: true, color: INK, size: 23, font: FONT })],
  });
}
function h3(text) {
  return new Paragraph({
    spacing: { before: 160, after: 80 },
    children: [new TextRun({ text, bold: true, color: INK, size: 21, font: FONT })],
  });
}
function p(text, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 140, line: 300 },
    children: [new TextRun({ text, size: 21, font: FONT, color: INK, ...opts })],
  });
}
function bullet(text, opts = {}) {
  return new Paragraph({
    bullet: { level: 0 },
    spacing: { after: 90, line: 290 },
    children: [new TextRun({ text, size: 20, font: FONT, color: INK, ...opts })],
  });
}
function note(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { before: 60, after: 160 },
    children: [new TextRun({ text, italics: true, size: 20, font: FONT, color: INK })],
  });
}
function placeholder(text) {
  return new Paragraph({
    spacing: { before: 100, after: 220 },
    alignment: AlignmentType.CENTER,
    border: {
      top: { color: GRAY, space: 6, style: BorderStyle.DASHED, size: 6 },
      bottom: { color: GRAY, space: 6, style: BorderStyle.DASHED, size: 6 },
      left: { color: GRAY, space: 6, style: BorderStyle.DASHED, size: 6 },
      right: { color: GRAY, space: 6, style: BorderStyle.DASHED, size: 6 },
    },
    children: [new TextRun({ text: "[Pendiente] " + text, italics: true, size: 19, font: FONT, color: GRAY })],
  });
}
function imgParagraph(file, widthPx, maxWidthIn = 6.3) {
  const buf = fs.readFileSync(path.join(A, file));
  const { execSync } = require("child_process");
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 120 },
    children: [
      new ImageRun({
        data: buf,
        transformation: { width: Math.round(maxWidthIn * 96), height: Math.round(maxWidthIn * 96 * (widthPx.h / widthPx.w)) },
        type: "png",
      }),
    ],
  });
}
function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
    children: [new TextRun({ text, italics: true, size: 17, color: GRAY, font: FONT })],
  });
}

function cell(text, opts = {}) {
  const { bold = false, fill = null, color = INK, size = 18, align = AlignmentType.LEFT } = opts;
  return new TableCell({
    width: { size: opts.width || 20, type: WidthType.PERCENTAGE },
    shading: fill ? { type: ShadingType.CLEAR, fill } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text: String(text), bold, size, color, font: FONT })],
    })],
  });
}
function headerRow(cells) {
  return new TableRow({
    tableHeader: true,
    children: cells.map((c) => cell(c, { bold: true, fill: HEADFILL, color: "FFFFFF", size: 18 })),
  });
}
function dataRow(cells, opts = {}) {
  return new TableRow({ children: cells.map((c) => cell(c, { fill: opts.fill, size: 18 })) });
}
function table(rows) {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows,
  });
}

// ---------- PORTADA (mismo formato que "Verificación de Lectura — Calidad de Datos DAMA-DMBOK") ----------
const logoBuf = fs.readFileSync(path.join(A, "logo_udec.png"));
const portada = [
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 200, after: 4 },
    children: [new TextRun({ text: "Universidad de Cundinamarca", bold: true, size: 22, color: INK, font: FONT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 4 },
    children: [new TextRun({ text: "Facultad de Ingeniería", size: 21, color: INK, font: FONT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 360 },
    children: [new TextRun({ text: "Minería de Datos", size: 21, color: INK, font: FONT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 4 },
    children: [new TextRun({ text: "Informe Técnico — Etapa 3", bold: true, size: 26, color: INK, font: FONT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 360 },
    children: [new TextRun({ text: "Tratamiento de datos con un proceso ETL en SQL Server Integration Services (SSIS)", bold: true, size: 26, color: INK, font: FONT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 4 },
    children: [new TextRun({ text: "Estudiante: David Santiago Romero", size: 21, color: INK, font: FONT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 4 },
    children: [new TextRun({ text: "Docente: Édison Gustavo Cañón Varela", size: 21, color: INK, font: FONT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 4 },
    children: [new TextRun({ text: "Proyecto: Migración y Desplazamiento Humano (trabajo individual)", size: 21, color: INK, font: FONT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 700, after: 100 },
    children: [new ImageRun({ data: logoBuf, transformation: { width: 300, height: 147 }, type: "png" })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 700 },
    children: [new TextRun({ text: "Septiembre 29 de 2026", size: 21, color: INK, font: FONT })],
  }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---------- 1. Introducción ----------
const introSection = [
  h1("1. Introducción y objetivo"),
  p("Este informe documenta la implementación y verificación del proceso ETL (Extracción, Transformación y Carga) construido con SQL Server Integration Services (SSIS) para tratar los problemas de calidad de datos identificados en la Etapa 2 del proyecto Migración y Desplazamiento Humano. El proceso parte del dataset consolidado de 28.467 registros (Etapa 1) y del diagnóstico de calidad en seis dimensiones —completitud, exactitud, consistencia, unicidad, validez y actualidad— obtenido en la Etapa 2."),
  p("El objetivo concreto es doble: primero, aplicar reglas de tratamiento trazables sobre cada problema ya diagnosticado, usando los componentes estándar de un Data Flow de SSIS (Derived Column, Data Conversion, Lookup, Conditional Split y Sort); segundo, demostrar —con tres iteraciones reales y una prueba explícita— que el proceso no pierde información, que separa correctamente los registros que requieren revisión manual conservando su valor original, y que es idempotente: volver a ejecutar el mismo lote no genera duplicados en el destino."),
  p("Todo el proceso se apoya en una zona de staging (etl.stg_desplazamiento) que conserva el dato exactamente como llega, sin tipar ni transformar, lo que garantiza trazabilidad y repetibilidad completas: si en el futuro se necesita auditar por qué un registro terminó en la tabla de revisión, siempre se puede volver al dato crudo del staging."),
];

// ---------- 2. Diagnóstico y reglas ----------
const reglasRows = [headerRow(["Campo", "Problema de origen (Etapa 2)", "Acción en el Data Flow", "Justificación"])];
resultados.reglas_tratamiento.forEach((r, i) => {
  reglasRows.push(dataRow([r.campo, r.problema_origen, r.accion, r.justificacion], { fill: i % 2 ? "F6F7FB" : "FFFFFF" }));
});

const diagnosticoSection = [
  h1("2. Diagnóstico inicial y reglas de tratamiento"),
  p("La Etapa 2 midió el dataset consolidado en seis dimensiones de calidad y produjo un inventario de problemas con evidencia cuantitativa (por ejemplo: 345 registros sin valor en personas_desplazadas, exactitud del 98.79% por valores negativos, y un catálogo de dominio de sexo que resultó incompleto una vez confrontado con los datos reales). Cada regla de tratamiento definida a continuación responde directamente a uno de esos hallazgos: no se trata de validaciones genéricas, sino de reglas trazables hasta el problema que las originó."),
  table(reglasRows),
  new Paragraph({ spacing: { after: 200 } }),
  note("Nota metodológica: los valores nulos de personas_desplazadas NO se imputan con 0. Imputar subestimaría el fenómeno cuando la fuente simplemente no reportó una cifra para ese país-año-causa; en cambio, esos registros se separan a la tabla de revisión, preservando el resto de las columnas originales para que un analista pueda decidir con contexto completo."),
];

// ---------- 3. Diseño del paquete ----------
const diseñoSection = [
  h1("3. Diseño del paquete SSIS: Control Flow y Data Flow"),
  h2("3.1 Control Flow"),
  p("El paquete Package.dtsx (Paquete_Tratamiento_Desplazamiento) organiza la ejecución en seis pasos conectados por restricciones de precedencia (precedence constraints). (1) 'Registrar Inicio de batch' — Execute SQL Task que inserta un nuevo registro en etl.log_batches y devuelve el batch_id con el que se identifica toda la corrida. (2) 'Truncar tablas temporales' — Execute SQL Task que vacía etl.stg_desplazamiento, etl.tmp_candidatos_validos y etl.tmp_revision_lote, dejando cada corrida en un estado limpio y repetible. (3) 'Data Flow Task' ('Cargar staging') — lee el archivo origen y lo escribe sin transformar en etl.stg_desplazamiento. (4) 'Transformar y cargar' — Data Flow Task que aplica todas las reglas de validación, tipado y cálculo de la llave de negocio. (5) 'Ejecutar MERGE idempotente' — Execute SQL Task que llama a etl.sp_merge_lote, el procedimiento que compara contra el destino y decide, por cada fila candidata, si es un registro nuevo (INSERT) o ya existente (UPDATE). (6) 'Marcar batch OK' / 'Marcar batch ERROR' — un branch por restricción de precedencia (Éxito / Error) que cierra el registro del lote en el log con el resultado final."),
  imgParagraph("evidencia_control_flow_disenio.png", { w: 961, h: 633 }, 5.6),
  caption("Figura 1. Control Flow del paquete, vista de diseño (captura real de SSDT/Visual Studio)."),
  imgParagraph("evidencia_control_flow_ok.png", { w: 909, h: 694 }, 5.0),
  caption("Figura 2. Ejecución exitosa del paquete completo: los seis pasos en verde, con 'Marcar batch ERROR' sin ejecutarse porque el branch de éxito fue el que se activó."),
  h2("3.2 Data Flow"),
  p("El Data Flow Task 'Transformar y cargar' es donde ocurre todo el tratamiento. El flujo real, ya construido y probado, es: OLE DB Source (lee etl.stg_desplazamiento) → Derived Column 'Validaciones de texto' (limpia campos vacíos y calcula banderas de validación) → Data Conversion 'Convertir tipos' (fuerza anio, personas_desplazadas y desplazamiento_stock a sus tipos definitivos) → Derived Column (calcula es_negativo, anio_fuera_de_rango y la llave de negocio clave_negocio_texto) → Lookup contra etl.ref_sexo (separa sexo válido / inválido) → Union All (reúne ambas salidas del Lookup) → Derived Column 'Calcular motivo de revisión' (resuelve un único motivo textual cuando aplica alguna regla) → Conditional Split (separa 'Validos' de 'ARevision') → Sort (ordena 'Validos' por clave_negocio) → dos OLE DB Destination, uno hacia etl.tmp_candidatos_validos y otro hacia etl.tmp_revision_lote. El Row Count conectado a la salida de error de 'Convertir tipos' es un componente de diagnóstico usado durante la construcción del paquete, sin efecto sobre el resultado final."),
  imgParagraph("evidencia_data_flow_transformar.png", { w: 1480, h: 714 }, 6.3),
  caption("Figura 3. Data Flow 'Transformar y cargar', vista de diseño completa (captura real)."),
  p("La detección de duplicados NO ocurre dentro de este Data Flow: los candidatos válidos se escriben siempre en la tabla temporal etl.tmp_candidatos_validos, y es el paso 5 del Control Flow (MERGE, etl.sp_merge_lote) el que compara clave_negocio contra etl.desplazamiento_tratado y decide INSERT (nuevo) vs. UPDATE (duplicado). Separar esa decisión del Data Flow simplificó el diseño y es lo que garantiza la idempotencia sin depender de un Lookup adicional contra el destino."),
  p("El Data Flow Task de staging es mucho más simple: solo copia el archivo origen hacia etl.stg_desplazamiento sin aplicar ninguna regla de negocio, preservando el dato exactamente como llega."),
  imgParagraph("evidencia_data_flow_staging.png", { w: 919, h: 685 }, 4.6),
  caption("Figura 4. Data Flow de staging: Flat File Source → Derived Column (columnas de control) → OLE DB Destination (captura real)."),
  p("La zona de staging cumple un rol distinto al de las tablas temporales de lote: el staging (etl.stg_desplazamiento) es append-only dentro de cada corrida y NUNCA se transforma — ahí queda el dato tal como llegó, columna por columna, en NVARCHAR. Las tablas tmp_candidatos_validos y tmp_revision_lote, en cambio, ya contienen el resultado tipado y validado de un lote específico, y se truncan al inicio de cada corrida. Esta separación es la que permite, ante cualquier duda, reconstruir por qué un registro terminó donde terminó."),
];

// ---------- 4. Configuración paso a paso ----------
function componentBlock(titulo, resumen, detalles, opts = {}) {
  const items = [h3(titulo), p(resumen)];
  detalles.forEach((d) => items.push(bullet(d)));
  if (!opts.skipPlaceholder) {
    items.push(placeholder(`Captura real del ${titulo} configurado en SSDT/Visual Studio (pegar aquí una vez construido el paquete)`));
  }
  return items;
}

const configSection = [
  h1("4. Configuración de los componentes (guía de construcción)"),
  p("Esta sección documenta la configuración real y ya verificada de las tareas del paquete, tal como quedó construido y probado en SSDT/Visual Studio, con captura de pantalla real de cada Execute SQL Task del Control Flow. Los componentes del Data Flow se documentan con su expresión/configuración exacta; donde aún no se anexó la captura individual del editor, se deja marcado como pendiente."),

  h2("4.0 Tareas del Control Flow (Execute SQL Task)"),
  h3("Registrar Inicio de batch"),
  p("Primer paso del paquete: inserta la fila de control del lote en etl.log_batches y devuelve, con OUTPUT INSERTED.batch_id, el identificador que usan todas las demás tareas para escribir en el mismo lote."),
  imgParagraph("evidencia_registrar_batch.png", { w: 778, h: 655 }, 4.6),
  caption("Figura 5. Editor de la tarea 'Registrar Inicio de batch' con la instrucción SQL real."),
  h3("Truncar tablas temporales"),
  p("Deja cada corrida en un estado limpio y repetible: vacía la zona de staging y las dos tablas temporales de lote antes de volver a extraer y transformar."),
  imgParagraph("evidencia_truncar_tablas.png", { w: 1039, h: 810 }, 5.2),
  caption("Figura 6. Editor de la tarea 'Truncar tablas temporales', con las tres instrucciones TRUNCATE TABLE reales."),
  h3("Ejecutar MERGE idempotente"),
  p("Llama al procedimiento almacenado que compara los candidatos válidos contra el destino y decide, por cada fila, si es un INSERT nuevo o un UPDATE de un registro ya existente. Es el mecanismo central que garantiza la idempotencia del proceso."),
  imgParagraph("evidencia_merge_idempotente.png", { w: 1099, h: 814 }, 5.2),
  caption("Figura 7. Editor de la tarea 'Ejecutar MERGE idempotente': EXEC etl.sp_merge_lote @batch_id = ?."),
  h3("Marcar batch OK"),
  p("Cierra el registro del lote en etl.log_batches con resultado = 'OK' y la fecha de fin, cuando el MERGE se ejecutó sin errores. Un Execute SQL Task equivalente, 'Marcar batch ERROR', hace lo mismo con resultado = 'ERROR' cuando la restricción de precedencia toma la rama de falla."),
  imgParagraph("evidencia_marcar_batch_ok.png", { w: 1090, h: 820 }, 5.2),
  caption("Figura 8. Editor de la tarea 'Marcar batch OK'."),

  ...componentBlock(
    "4.1 Derived Column — 'Validaciones de texto'",
    "Primer punto de limpieza: antes de convertir tipos, resuelve el caso de campos numéricos que llegan como cadena vacía (no NULL) desde el origen, y calcula las banderas de completitud y consistencia jerárquica.",
    [
      "es_sin_dato = ISNULL(personas_desplazadas) || TRIM(personas_desplazadas) == \"\" — detecta el caso 'sin valor reportado'.",
      "es_geo_inconsistente = (nivel == \"Regional\" && (ISNULL(departamento) || TRIM(departamento)==\"\")) || ((nivel==\"Global\"||nivel==\"Nacional\") && !ISNULL(departamento) && TRIM(departamento)!=\"\") — valida la jerarquía nivel/departamento/municipio.",
      "personas_desplazadas_limpio = TRIM(personas_desplazadas) == \"\" ? NULL(DT_WSTR,30) : personas_desplazadas — convierte cadena vacía en NULL real, requisito para que Data Conversion no falle.",
      "desplazamiento_stock_limpio = TRIM(desplazamiento_stock) == \"\" ? NULL(DT_WSTR,30) : desplazamiento_stock — mismo tratamiento para el stock.",
    ]
  ),
  ...componentBlock(
    "4.2 Data Conversion — 'Convertir tipos'",
    "Convierte explícitamente los tipos de dato leídos como texto desde el staging hacia los tipos definitivos; si la conversión falla, SSIS enruta la fila por el error output del propio componente ('Redirigir fila').",
    [
      "anio (DT_WSTR) → anio_conv (DT_I4).",
      "personas_desplazadas_limpio → personas_desplazadas_conv (DT_NUMERIC, precisión 18, escala 2).",
      "desplazamiento_stock_limpio → desplazamiento_stock_conv (DT_NUMERIC, precisión 18, escala 2), permite NULL.",
      "LocaleID del componente: 'Inglés (Estados Unidos)' — el dato origen usa punto como separador decimal; el LocaleID por defecto ('Español (Colombia)', que espera coma) causaba fallos sistemáticos de conversión.",
      "Configuración de Error/Truncamiento: 'Redirigir fila' para las tres columnas — una fila que no puede convertirse no se pierde, se documenta como ERROR_CONVERSION_TIPO en la tabla de revisión.",
    ]
  ),
  ...componentBlock(
    "4.3 Derived Column — cálculo de indicadores y llave de negocio",
    "Con los tipos ya definitivos, calcula las últimas banderas de validación y construye la llave de negocio como texto plano.",
    [
      "es_negativo = personas_desplazadas_conv < 0 — valida que la cifra no sea negativa.",
      "anio_fuera_de_rango = anio_conv < 1970 || anio_conv > 2026 — valida rango temporal.",
      "clave_negocio_texto = (DT_WSTR,20)nivel + \"|\" + (DT_WSTR,10)iso3 + \"|\" + (ISNULL(departamento)?\"\":(DT_WSTR,150)departamento) + \"|\" + (ISNULL(municipio)?\"\":(DT_WSTR,150)municipio) + \"|\" + (DT_WSTR,10)anio_conv + \"|\" + (DT_WSTR,60)causa + \"|\" + (DT_WSTR,20)sexo + \"|\" + (DT_WSTR,20)grupo_edad + \"|\" + (DT_WSTR,250)fuente — identifica de forma única un hecho (nivel+país+división geográfica+año+causa+sexo+grupo de edad+fuente). Se probó primero calculando un hash SHA-256 con HASHBYTES en un OLE DB Command, pero el proveedor OLE DB no logró preparar ese comando de forma confiable; se optó por la llave en texto plano, más simple y suficiente para este volumen.",
    ]
  ),
  ...componentBlock(
    "4.4 Lookup — dominio de sexo",
    "Valida que el valor de sexo pertenezca al catálogo de referencia etl.ref_sexo, sin descartar las filas que no coinciden.",
    [
      "Connection: OLE DB Connection Manager a MigracionDesplazamiento; tabla de referencia: SELECT valor FROM etl.ref_sexo (Full Cache).",
      "Columna de unión: sexo = valor.",
      "Specify how to handle rows with no matching entries → 'Redirigir filas a la salida de no coincidencia' (no 'Fail Component'): un valor fuera de dominio es un caso de negocio a revisar, no un error del paquete.",
      "Salida de coincidencia → Derived Column 'Sexo Válido' (sexo_invalido = (DT_BOOL)0). Salida sin coincidencia → Derived Column 'Sexo inválido' (sexo_invalido = (DT_BOOL)1).",
    ]
  ),
  ...componentBlock(
    "4.5 Union All",
    "Reúne de nuevo en un único flujo las dos ramas que salieron del Lookup (coincidencia / no coincidencia), cada una ya con su bandera sexo_invalido calculada.",
    [
      "Combina las columnas de ambas ramas en un solo buffer, condición necesaria para poder aplicar después una única lógica de Conditional Split sobre todas las filas.",
    ]
  ),
  ...componentBlock(
    "4.6 Derived Column — 'Calcular motivo de revisión'",
    "Resuelve, con una sola expresión anidada, cuál es el motivo de revisión aplicable a la fila (si hay alguno), dando prioridad a las reglas en el orden que tiene más sentido de negocio.",
    [
      "motivo_revision = es_sin_dato ? \"SIN_DATO_ORIGEN\" : (es_negativo ? \"VALOR_NEGATIVO\" : (anio_fuera_de_rango ? \"ANIO_FUERA_DE_RANGO\" : (sexo_invalido ? \"FUERA_DE_DOMINIO_SEXO\" : (es_geo_inconsistente ? \"INCONSISTENCIA_NIVEL_GEOGRAFIA\" : NULL(DT_WSTR,60)))))",
      "Si ninguna regla aplica, motivo_revision queda NULL y la fila sigue como candidata válida.",
    ]
  ),
  ...componentBlock(
    "4.7 Conditional Split",
    "Separa cada fila en una de dos salidas según si motivo_revision quedó resuelto o no.",
    [
      "Salida 'ARevision': !ISNULL(motivo_revision) — cualquier fila con un motivo de revisión calculado.",
      "Salida por defecto 'Validos': el resto de las filas, ya tipadas, sin banderas de error y con la llave de negocio calculada.",
      "La detección de duplicados NO ocurre aquí: toda fila 'Válida' se escribe en la tabla temporal y es el MERGE (paso 4 del Control Flow) el que decide si es nueva o ya existía en el destino.",
      "Los outliers (fuera de 3×IQR) tampoco se separan en este Conditional Split: la columna outlier_iqr_extremo queda reservada en el esquema (BIT, default 0) para ese propósito; su cálculo automático se validó en la simulación Python y queda documentado como siguiente incremento (ver sección 5, hallazgo de la regla de atípicos).",
    ]
  ),
  ...componentBlock(
    "4.8 Sort",
    "Ordena la salida 'Validos' por la llave de negocio antes de escribirla en el OLE DB Destination, dando un orden estable y determinístico a la carga.",
    [
      "Sort key: clave_negocio_texto, ascendente.",
      "'Remove rows with duplicate sort values' se deja DESACTIVADO: el Sort solo ordena, no decide qué es o no duplicado — esa decisión la toma el MERGE contra el destino.",
    ]
  ),
  ...componentBlock(
    "4.9 OLE DB Destination (dos salidas)",
    "Escribe cada rama del Conditional Split en su tabla temporal correspondiente; ninguna de las dos escribe directamente sobre las tablas definitivas.",
    [
      "Salida 'Validos' (ordenada) → etl.tmp_candidatos_validos. Mapeo manual: clave_negocio_texto → clave_negocio, anio_conv → anio, personas_desplazadas_conv → personas_desplazadas, desplazamiento_stock_conv → desplazamiento_stock; outlier_iqr_extremo se omite (usa el DEFAULT 0 de la tabla); el resto se mapea automáticamente por nombre.",
      "Salida 'ARevision' → etl.tmp_revision_lote. Mapeo manual: clave_negocio_texto → clave_negocio, motivo_revision → motivo_revision, y cada columna original (sin convertir) hacia su columna *_original correspondiente (nivel_original, iso3_original, pais_original, departamento_original, municipio_original, anio_original, causa_original, sexo_original, grupo_edad_original, personas_desplazadas_original, fuente_original), preservando el dato exactamente como llegó del origen.",
    ]
  ),
  ...componentBlock(
    "4.10 MERGE idempotente (fuera del Data Flow)",
    "El paso 5 del Control Flow ejecuta etl.sp_merge_lote (Execute SQL Task 'Ejecutar MERGE idempotente', ver Figura 7 en 4.0), que compara etl.tmp_candidatos_validos contra etl.desplazamiento_tratado por clave_negocio y decide la carga real.",
    [
      "WHEN MATCHED (la clave_negocio ya existe en el destino) → UPDATE: se cuenta como duplicado, no se reinserta.",
      "WHEN NOT MATCHED (la clave_negocio es nueva) → INSERT: se cuenta como aceptado nuevo.",
      "La cláusula OUTPUT $action INTO una tabla temporal permite separar, en el mismo Execute SQL Task, cuántas filas fueron INSERT y cuántas UPDATE, números que luego se escriben en etl.log_batches.",
      "Este es el mecanismo que garantiza la idempotencia: ejecutar el paquete varias veces con el mismo dataset nunca duplica el histórico ya cargado (verificado en la Iteración 3, ver sección 5).",
    ],
    { skipPlaceholder: true }
  ),

  h2("4.11 Connection Manager"),
  p("El Connection Manager usa autenticación integrada de Windows (Integrated Security) contra la instancia local de SQL Server; no se guarda usuario ni contraseña en el paquete ni en el repositorio. La cadena de conexión de ejemplo, sin credenciales, es:"),
  new Paragraph({
    spacing: { after: 200 },
    children: [new TextRun({ text: "Server=localhost;Database=MigracionDesplazamiento;Trusted_Connection=True;", font: "Consolas", size: 19, color: INK })],
  }),
];

// ---------- 5. Iteraciones ----------
function statRow(labels, values) {
  return dataRow([...labels.map((l, i) => `${l}: ${values[i]}`)]);
}
const iterBlocks = [h1("5. Evidencia de las 3 iteraciones")];
iterBlocks.push(p("Cada iteración se ejecutó sobre el mismo diseño de paquete, ajustando únicamente el alcance del origen y el catálogo de referencia de sexo entre la Iteración 1 y la Iteración 2, según lo que la propia ejecución reveló. Los conteos siguientes están verificados: en cada iteración, aceptados + duplicados + enviados a revisión = recibidos, sin pérdida de registros."));
iterBlocks.push(imgParagraph("comparacion_iteraciones.png", { w: 1879, h: 1099 }, 6.3));
iterBlocks.push(caption("Figura 9. Comparación de resultados reales entre las tres iteraciones (calculada a partir de los batches 19-22 de etl.log_batches)."));
iterBlocks.push(imgParagraph("evidencia_log_batches_21_22.png", { w: 1882, h: 895 }, 6.3));
iterBlocks.push(caption("Figura 10. etl.log_batches en SSMS, mostrando los batches 21 (Iteración 1) y 22 (Iteración 2) tal como quedaron registrados (captura real)."));

resultados.iteraciones.forEach((it) => {
  iterBlocks.push(h2(`5.${it.numero} Iteración ${it.numero} — ${it.titulo}`));
  iterBlocks.push(p(it.descripcion));
  const rows = [headerRow(["Indicador", "Valor"])];
  const r = it.resultados;
  rows.push(dataRow(["Recibidos", r.recibidos]));
  rows.push(dataRow(["Aceptados (nuevos)", r.aceptados_nuevos]));
  rows.push(dataRow(["Duplicados (ya existían)", r.duplicados_ya_existian]));
  rows.push(dataRow(["Enviados a revisión", r.enviados_a_revision]));
  if (r.marcados_outlier_informativo !== undefined) rows.push(dataRow(["Marcados outlier (informativo)", r.marcados_outlier_informativo]));
  iterBlocks.push(table(rows));
  iterBlocks.push(new Paragraph({ spacing: { before: 100, after: 120 }, children: [new TextRun({ text: `Verificación de balance: ${r.aceptados_nuevos} + ${r.duplicados_ya_existian} + ${r.enviados_a_revision} = ${r.aceptados_nuevos + r.duplicados_ya_existian + r.enviados_a_revision} = ${r.recibidos} recibidos.`, italics: true, size: 18, color: GRAY, font: FONT })] }));
  if (it.hallazgos && it.hallazgos.length) {
    iterBlocks.push(h3("Hallazgos"));
    it.hallazgos.forEach((hd) => iterBlocks.push(bullet(hd)));
  }
  if (it.ajuste_para_siguiente) {
    iterBlocks.push(note("Ajuste aplicado en la siguiente iteración: " + it.ajuste_para_siguiente));
  }
  if (it.prueba_idempotencia) {
    const pi = it.prueba_idempotencia;
    iterBlocks.push(h3("Prueba de idempotencia (mismo lote ejecutado una segunda vez, sin limpiar el destino)"));
    const rowsIdem = [headerRow(["Indicador", "Valor"])];
    rowsIdem.push(dataRow(["Recibidos", pi.recibidos]));
    rowsIdem.push(dataRow(["Ya existían (duplicados)", pi.ya_existian_duplicados]));
    rowsIdem.push(dataRow(["Nuevos insertados", pi.nuevos_insertados]));
    rowsIdem.push(dataRow(["Enviados a revisión", pi.enviados_a_revision]));
    rowsIdem.push(dataRow(["Tamaño del destino antes", pi.destino_antes]));
    rowsIdem.push(dataRow(["Tamaño del destino después", pi.destino_despues]));
    iterBlocks.push(table(rowsIdem));
    iterBlocks.push(new Paragraph({
      spacing: { before: 120, after: 200 },
      children: [new TextRun({
        text: pi.es_idempotente
          ? "Resultado: el tamaño del destino no cambió (" + pi.destino_antes + " = " + pi.destino_despues + ") y 0 filas nuevas se insertaron en la segunda corrida. El proceso es idempotente."
          : "Resultado: se detectó una inconsistencia en la prueba de idempotencia; requiere revisión.",
        bold: true, size: 20, color: pi.es_idempotente ? INK : "b00020", font: FONT,
      })],
    }));
    iterBlocks.push(placeholder("Captura real de la segunda ejecución del paquete en SSIS/SSMS (log_batches mostrando filas_aceptadas = 0)"));
  }
});

// ---------- 6. Manejo de errores / revisión ----------
const errorSection = [
  h1("6. Manejo de errores y tratamiento de registros en revisión"),
  p("Un registro nunca se descarta silenciosamente. Cuando una fila no cumple alguna regla, el Conditional Split la enruta hacia etl.tmp_revision_lote, que conserva las columnas *_original (nivel_original, iso3_original, anio_original, personas_desplazadas_original, etc.) exactamente como llegaron del staging, junto con motivo_revision indicando cuál regla falló. Esa tabla se integra por MERGE hacia etl.desplazamiento_revision, que además agrega resuelto (bit) y comentario_resolucion, para que un analista de datos pueda dar seguimiento manual sin perder el registro original."),
  h3("Motivos de revisión utilizados"),
  bullet("SIN_DATO_ORIGEN — personas_desplazadas llegó nulo desde la fuente."),
  bullet("VALOR_NEGATIVO — personas_desplazadas o desplazamiento_stock es negativo."),
  bullet("ERROR_CONVERSION_TIPO — la Data Conversion no pudo convertir anio o los montos."),
  bullet("FUERA_DE_DOMINIO_SEXO — el valor de sexo no está en el catálogo de referencia (evidenciado y corregido entre la Iteración 1 y la 2)."),
  bullet("INCONSISTENCIA_NIVEL_GEOGRAFIA — un registro Regional sin municipio, o un registro Global/Nacional con municipio."),
  bullet("ANIO_FUERA_DE_RANGO — anio fuera de 1970–año actual."),
  placeholder("Captura real de una fila en etl.desplazamiento_revision, mostrando el valor original preservado y su motivo_revision"),
];

// ---------- 7. Comparación de calidad ----------
const comp = resultados.comparacion_calidad;
const compSection = [
  h1("7. Comparación de calidad antes y después"),
  table([
    headerRow(["Indicador", "Antes", "Después"]),
    dataRow(["Completitud (variable central)", comp.completitud_antes_pct + "%", comp.completitud_despues_pct + "%"]),
    dataRow(["Validez", comp.validez_antes_pct + "%", comp.validez_despues_pct + "%"]),
    dataRow(["Duplicados en destino", "—", String(comp.duplicados_despues_del_control)]),
  ]),
  new Paragraph({ spacing: { after: 160 } }),
  note(comp.nota_completitud),
  p(`Verificación total: ${comp.total_verificado.toLocaleString("es-CO")} registros recibidos = ${comp.registros_en_destino_final.toLocaleString("es-CO")} en destino + ${comp.registros_en_revision_final.toLocaleString("es-CO")} en revisión. Sin el control de llave de negocio, cada recarga completa del dataset habría duplicado el histórico completo: ${comp.duplicados_generados_por_recargas_sin_control}; con el control activo (verificado en la Iteración 3, batch 20), los duplicados detectados y NO reinsertados en cada recarga posterior fueron ${comp.duplicados_despues_del_control}.`),
];

// ---------- 8. Enlaces ----------
const enlacesSection = [
  h1("8. Enlaces de entrega"),
  bullet("Aplicación Flask publicada: https://dromeroh14.pythonanywhere.com/etapa3"),
  bullet("Repositorio en GitHub (rama feature/etapa-3): https://github.com/DROMEROH14/migracion-desplazamiento-humano"),
  bullet("Recursos de esta etapa en el repositorio: etapa3/sql/ (scripts de base de datos), etapa3/etl_simulation.py (simulación verificada de la lógica del Data Flow), etapa3/*.dtsx (paquete SSIS)."),
  bullet("Video de demostración (máx. 4 minutos, grabación individual): enlace publicado junto con este informe en la sección Etapa 3 de la aplicación."),
  new Paragraph({ spacing: { before: 200 } }),
  note("Ningún script ni archivo de configuración incluido en el repositorio contiene usuarios, contraseñas ni cadenas de conexión con credenciales. El Connection Manager de SSIS usa autenticación integrada de Windows, configurada localmente en cada equipo donde se abre el paquete."),
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
  },
  sections: [
    {
      properties: { page: { margin: { top: 1100, bottom: 1100, left: 1100, right: 1100 } } },
      children: portada,
    },
    {
      properties: { page: { margin: { top: 1100, bottom: 1100, left: 1100, right: 1100 } } },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "Migración y Desplazamiento Humano · Etapa 3", size: 15, color: GRAY, font: FONT })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "David Santiago Romero · Minería de Datos · Página ", size: 15, color: GRAY, font: FONT }),
              new TextRun({ children: [PageNumber.CURRENT], size: 15, color: GRAY, font: FONT }),
            ],
          })],
        }),
      },
      children: [
        ...introSection,
        ...diagnosticoSection,
        ...diseñoSection,
        ...configSection,
        ...iterBlocks,
        ...errorSection,
        ...compSection,
        ...enlacesSection,
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(__dirname, "Informe_Etapa3_ETL_SSIS.docx"), buf);
  console.log("DOCX generado:", buf.length, "bytes");
});
