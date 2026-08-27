# Migración y Desplazamiento Humano — Etapa 1

Bitácora técnica en Flask del proyecto de Minería de Datos. Trabajo individual.

**Tema asignado:** Migración y Desplazamiento Humano
**Autor(a):** _(reemplazar con tu nombre)_

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

## 3. Publicar la aplicación (Flask en vivo)

La app es un proyecto Flask estándar, así que puedes desplegarla en cualquier plataforma que soporte Python. Dos opciones sencillas y gratuitas:

### Opción A — Render.com (recomendada, gratis)

1. Crea una cuenta en https://render.com y conecta tu cuenta de GitHub.
2. "New +" → "Web Service" → selecciona tu repositorio.
3. Configura:
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Deploy. Render te dará una URL pública tipo `https://tu-proyecto.onrender.com`.
5. Cada `git push` a `main` vuelve a desplegar automáticamente.

### Opción B — PythonAnywhere (gratis, sencillo para Flask)

1. Crea una cuenta en https://www.pythonanywhere.com
2. Sube el repo (`git clone` desde la consola Bash de PythonAnywhere) o sube el .zip.
3. Crea una app Web nueva → Framework Flask → apunta el WSGI file al `app.py`.
4. Instala dependencias: `pip install --user -r requirements.txt`
5. Recarga la app web; queda publicada en `https://tu-usuario.pythonanywhere.com`.

### Opción C — Railway.app

1. https://railway.app → "New Project" → "Deploy from GitHub repo".
2. Railway detecta el `Procfile` automáticamente y despliega.
3. Genera dominio público desde "Settings → Networking → Generate Domain".

## 4. Checklist de entrega

- [ ] Repositorio accesible en GitHub.
- [ ] Rama `feature/etapa-1` con historial de commits incrementales.
- [ ] Merge de `feature/etapa-1` a `main` realizado.
- [ ] Aplicación Flask publicada (URL funcionando).
- [ ] Las 8 secciones del menú "Etapa 1" cargan correctamente.
- [ ] `data/dataset_consolidado.csv` tiene ≥10.000 registros y ≥10 variables (cumplido: ~28.000 registros, 16 variables).
