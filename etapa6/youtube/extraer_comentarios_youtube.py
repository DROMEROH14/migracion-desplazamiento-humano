"""Extrae comentarios de primer nivel de un video de YouTube (YouTube Data API v3).

Uso (la clave NO se escribe en el codigo):
    Windows PowerShell:  $env:YOUTUBE_API_KEY="su_clave"; python extraer_comentarios_youtube.py ID_DEL_VIDEO
    Linux / macOS:       YOUTUBE_API_KEY=su_clave python extraer_comentarios_youtube.py ID_DEL_VIDEO

Salida: comentarios_youtube.csv (texto, fecha, likes). No se guarda el autor.
"""
import os
import sys
from datetime import date

import pandas as pd
import requests

API_KEY = os.environ.get("YOUTUBE_API_KEY")
VIDEO_ID = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VIDEO_ID")  # id del video: parte final de ?v=...
MAX_COMENTARIOS = 500
URL = "https://www.googleapis.com/youtube/v3/commentThreads"

if not VIDEO_ID:
    sys.exit("Indique el id del video: python extraer_comentarios_youtube.py ID_DEL_VIDEO")
if not API_KEY:
    sys.exit("Defina la variable de entorno YOUTUBE_API_KEY (no escriba la clave en el codigo).")

comentarios, pagina = [], None
while len(comentarios) < MAX_COMENTARIOS:
    params = {
        "key": API_KEY,
        "part": "snippet",
        "videoId": VIDEO_ID,
        "maxResults": min(100, MAX_COMENTARIOS - len(comentarios)),
        "textFormat": "plainText",
        "order": "time",
    }
    if pagina:
        params["pageToken"] = pagina
    r = requests.get(URL, params=params, timeout=30)
    datos = r.json()
    if r.status_code != 200:
        print("Error:", datos.get("error", {}).get("message"))
        break
    for it in datos.get("items", []):
        c = it["snippet"]["topLevelComment"]["snippet"]
        comentarios.append({"texto": c["textDisplay"], "fecha": c["publishedAt"], "likes": c["likeCount"]})
    pagina = datos.get("nextPageToken")
    if not pagina:
        break

if comentarios:
    df = pd.DataFrame(comentarios)
    df.to_csv("comentarios_youtube.csv", index=False, encoding="utf-8-sig")
    print(f"Comentarios guardados: {len(df)} | fecha de extraccion: {date.today().isoformat()}")
else:
    print("No se descargaron comentarios. Revise la clave y el video.")
