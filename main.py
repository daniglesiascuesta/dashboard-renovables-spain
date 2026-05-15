import requests
import anthropic
import json
import os
# DEBUG — verificar variables de entorno
print("ANTHROPIC_KEY existe:", bool(os.environ.get("ANTHROPIC_API_KEY")))
print("SUPABASE_URL existe:", bool(os.environ.get("SUPABASE_URL")))
print("SUPABASE_KEY existe:", bool(os.environ.get("SUPABASE_KEY")))
print("Todas las vars de entorno con SUPA:", [k for k in os.environ if "SUPA" in k])
from bs4 import BeautifulSoup
from datetime import date, timedelta

# ============================================================
# CONFIGURACIÓN — las keys vienen de variables de entorno
# ============================================================
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
SUPABASE_URL  = os.environ.get("SUPABASE_URL")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY")
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
        max_tokens=800,
        messages=[{"role": "user", "content": f"""Eres un experto en regulación y tramitación administrativa del sector de energías renovables en España. Tu tarea es analizar publicaciones del BOE y extraer información estructurada con máxima precisión.

TEXTO DEL BOE:
{pub['titulo']}

INSTRUCCIONES DE EXTRACCIÓN:

1. tipo_tramite: Identifica el tipo de trámite administrativo usando EXCLUSIVAMENTE estos códigos:
   - "AAP" → Autorización Administrativa Previa
   - "AAC" → Autorización Administrativa de Construcción
   - "AAE" → Autorización Administrativa de Explotación
   - "DIA" → Declaración de Impacto Ambiental
   - "DUP" → Declaración de Utilidad Pública
   - "IP" → Información Pública
   - "AAP+DIA" → Tramitación conjunta AAP y DIA
   - "AAP+AAC" → Tramitación conjunta AAP y AAC
   - "MOD" → Modificación de proyecto
   - "TIT" → Cambio de titularidad
   - "RES" → Resolución administrativa
   - "LIC" → Licencia o permiso municipal
   - "OTRO" → Cualquier otro trámite

2. tecnologia: Tecnología principal del proyecto:
   - "Fotovoltaico" → plantas solares fotovoltaicas
   - "Eólico" → parques eólicos onshore
   - "Eólico offshore" → parques eólicos marinos
   - "BESS" → sistemas de almacenamiento por batería
   - "Hibridación" → proyectos que combinan dos o más tecnologías
   - "LAT" → línea de alta tensión / infraestructura de evacuación
   - "SET" → subestación eléctrica
   - "Termosolar" → plantas termosolares
   - "Hidráulica" → centrales hidroeléctricas
   - "OTRO" → tecnología no identificada

3. nombre_proyecto: Nombre oficial del proyecto exactamente como aparece en el texto, sin abreviar.

4. empresa_promotora: Razón social completa de la empresa promotora. Si aparecen varias, incluye la principal. null si no se menciona.

5. potencia_mw: Potencia en MW como número decimal. Convierte si aparece en kW (dividir entre 1000). null si no se menciona.

6. provincias: Lista con todas las provincias afectadas en español estándar con tildes correctas.

7. municipios: Lista con todos los municipios mencionados, si aparecen.

8. comunidades_autonomas: Lista con todas las comunidades autónomas afectadas, nombre oficial completo.

9. estado_administrativo: Estado exacto del trámite:
   - "Información pública" → en fase de exposición pública
   - "Autorizado" → resolución favorable emitida
   - "Denegado" → resolución desfavorable
   - "En tramitación" → en proceso sin resolución
   - "Modificación aprobada" → modificación de proyecto aprobada
   - "Caducado" → expediente caducado

10. organismo_publicador: Organismo que publica el anuncio (ej. "Ministerio para la Transición Ecológica", "Delegación del Gobierno en Castilla y León", etc.)

11. relevante_renovables: true si el proyecto es claramente del sector de energías renovables o infraestructura de evacuación asociada. false en caso contrario.

12. resumen: Resumen ejecutivo del trámite en máximo 2 frases, claro y directo, en español profesional.

REGLAS IMPORTANTES:
- Usa siempre caracteres españoles correctos: á, é, í, ó, ú, ñ, ü
- Si un campo no puede determinarse con certeza, devuelve null
- No inventes datos que no aparezcan explícitamente en el texto
- Las listas vacías se representan como []

Devuelve ÚNICAMENTE el JSON válido, sin texto adicional, sin bloques de código markdown."""}]
    )
    texto = mensaje.content[0].text.strip().removeprefix("```json").removesuffix("```").strip()
    datos = json.loads(texto)
    return json.loads(json.dumps(datos, ensure_ascii=False))
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
