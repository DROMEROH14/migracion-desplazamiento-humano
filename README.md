# Migración y Desplazamiento Humano — Etapa 1

Bitácora técnica en Flask del proyecto de Minería de Datos. Trabajo individual.

**Tema asignado:** Migración y Desplazamiento Humano
**Autor:** David Santiago Romero
**Repositorio GitHub:** https://github.com/DROMEROH14/migracion-desplazamiento-humano
**URL de la aplicación Flask publicada:** https://dromeroh14.pythonanywhere.com

## Contenido del repositorio

```
├── app.py                     # Aplicación Flask
├── requirements.txt
├── Procfile                   # Para despliegue en Render/Railway/Heroku
├── data/
│   ├── dataset_consolidado.csv        # Dataset integrado (≈28.000 registros)
│   ├── diccionario_datos.csv
│   ├── resumen_calidad.json
│   ├── fuentes.json
│   ├── Desplazamiento_forzado_Hist_C3_B3rico.csv          # Fuente cruda (CNMH)
│   └── idmc_internal_displacement_conflict-violence_disasters-39.xlsx  # Fuente cruda (IDMC)
├── scripts/
│   └── build_dataset.py       # Script reproducible que genera el dataset consolidado
├── static/css/style.css
└── templates/                 # Vistas de las 8 secciones de la Etapa 1
```

## 1. Ejecutar en local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (Opcional) regenerar el dataset consolidado a partir de las fuentes crudas
python scripts/build_dataset.py

python app.py
```

Abre http://localhost:5000

## 2. Publicar en GitHub (flujo individual, con ramas)

```bash
# 1. Inicializar repo (si aún no existe)
git init
git add .
git commit -m "chore: estructura inicial del proyecto Flask"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/<tu-repo>.git
git push -u origin main

# 2. Crear la rama de la Etapa 1
git checkout -b feature/etapa-1

# 3. Trabajar y hacer commits pequeños y descriptivos, por ejemplo:
git add templates/problema.html
git commit -m "feat: agregar módulo de problema y contexto"

git add templates/diccionario.html data/diccionario_datos.csv
git commit -m "docs: agregar diccionario de datos"

git add data/dataset_consolidado.csv scripts/build_dataset.py
git commit -m "data: construir y cargar dataset inicial consolidado"

git add templates/calidad.html
git commit -m "feat: agregar diagnóstico inicial de calidad"

# repite con commits pequeños por cada avance real (no todo en un solo commit)

# 4. Subir la rama
git push -u origin feature/etapa-1

# 5. Cuando esté validada, hacer merge a main
git checkout main
git merge feature/etapa-1
git push origin main
```

> Sugerencia: crea el Pull Request de `feature/etapa-1` hacia `main` en GitHub y haz el merge desde ahí — así queda visible el historial de la Etapa 1 como evidencia de trabajo incremental.

## 3. Despliegue en producción

La aplicación está publicada en PythonAnywhere:

**URL:** https://dromeroh14.pythonanywhere.com

Pasos seguidos para el despliegue:

1. Clonar el repositorio desde una consola Bash de PythonAnywhere.
2. Crear un entorno virtual e instalar las dependencias del `requirements.txt`.
3. Configurar la Web App (Manual configuration, Python 3.10) apuntando el
   *Source code* y el *Working directory* a la carpeta del proyecto, y el
   *Virtualenv* al entorno creado.
4. Editar el archivo WSGI para importar la aplicación Flask (`from app import app as application`).
5. Recargar la Web App.

Cada vez que se actualiza el código en `main`, se debe volver a la consola Bash
de PythonAnywhere, hacer `git pull` dentro de la carpeta del proyecto y recargar
la Web App desde la pestaña "Web".
