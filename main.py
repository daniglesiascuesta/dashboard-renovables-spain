import requests
import anthropic
import json
import os
from bs4 import BeautifulSoup
from datetime import date, timedelta

# ============================================================
# CONFIGURACIÓN — las keys vienen de variables de entorno
# ============================================================
ANTHROPIC_KEY = os.environ.get("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")
SUPABASE_URL  = os.environ.get("https://nlokctyrxuykzzlfnrvz.supabase.co")
SUPABASE_KEY  = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5sb2tjZnlyeHV5a3p6aWZucnZ6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg1NDEzOTMsImV4cCI6MjA5NDExNzM5M30.yk7OqKEgbSP4HSEIahtTR2M5_QtPY22ivcT71NA3wg4")

cliente = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ============================================================
# LEER EL BOE — si hoy no hay, usamos el día anterior
# ============================================================
def obtener_fecha_boe():
    for dias_atras in range(0, 5):
        fecha = date.today() - timedelta(days=dias_atras)
        url = f"https://www.boe.es/boe/dias/{fecha.strftime('%Y/%m/%d')}/"
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.find_all("li", class_="dispo")
        if len(items) > 0:
            print(f"✅ BOE encontrado: {fecha} — {len(items)} publicaciones")
            return items, str(fecha)
    return [], ""

# ============================================================
# FILTRAR PUBLICACIONES RELEVANTES
# ============================================================
keywords = [
    "fotovoltaic", "solar", "eólico", "eólica",
    "almacenamiento", "bess", "batería", "renovable",
    "evacuación", "subestación", "hibridación",
    "parque eólico", "planta solar", "autorización ambiental",
    "declaración impacto", "utilidad pública",
    "generación eléctrica", "industria y energía"
]

def filtrar_relevantes(items):
    relevantes = []
    for item in items:
        texto = item.get_text(strip=True).lower()
        enlace_tag = item.find("a", href=True)
        enlace = "https://www.boe.es" + enlace_tag["href"] if enlace_tag else ""
        for kw in keywords:
            if kw in texto:
                relevantes.append({"titulo": item.get_text(strip=True), "enlace": enlace})
                break
    print(f"✅ Relevantes detectados: {len(relevantes)}")
    return relevantes

# ============================================================
# CLASIFICAR CON CLAUDE
# ============================================================
def clasificar(pub):
    mensaje = cliente.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": f"""Analiza este texto del BOE y extrae datos en JSON.

Texto: {pub['titulo']}

Devuelve ÚNICAMENTE un JSON con:
- tipo_tramite, tecnologia, nombre_proyecto, empresa_promotora
- potencia_mw (número o null), provincias (lista), comunidades_autonomas (lista)
- estado_administrativo, relevante_renovables (true/false)

Solo el JSON, sin texto adicional."""}]
    )
    texto = mensaje.content[0].text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(texto)

# ============================================================
# GUARDAR EN SUPABASE
# ============================================================
def guardar_supabase(datos):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/proyectos",
        headers=headers,
        json=datos
    )
    if r.status_code in [200, 201]:
        print(f"✅ Guardado: {datos.get('nombre_proyecto')}")
    else:
        print(f"⚠️ Error guardando: {r.status_code} — {r.text}")

# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================
items, fecha = obtener_fecha_boe()
relevantes = filtrar_relevantes(items)

for pub in relevantes:
    try:
        datos = clasificar(pub)
        datos["enlace"] = pub["enlace"]
        datos["fecha_publicacion"] = fecha
        guardar_supabase(datos)
    except Exception as e:
        print(f"⚠️ Error procesando: {e}")

print("\n🎯 Proceso completado")
