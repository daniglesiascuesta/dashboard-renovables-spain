"""
Script de reprocesamiento de registros existentes en Supabase.
Descarga el PDF original de cada registro, extrae el texto completo
y reclasifica con Claude Haiku para enriquecer los datos incompletos.

Uso:
    python scripts/reprocesar_registros.py

Requisitos:
    - ANTHROPIC_API_KEY en el entorno
    - SUPABASE_URL en el entorno
    - SUPABASE_KEY en el entorno
"""

import os
import json
import time
import requests
from scrapers.boe_scraper import BOEScraper
from processor.classifier import Classifier
from database.supabase_client import SupabaseClient


def obtener_todos_los_registros(db: SupabaseClient) -> list[dict]:
    """Obtiene todos los registros de Supabase ordenados por id."""
    respuesta = requests.get(
        f"{db.url}/rest/v1/proyectos",
        headers=db.headers,
        params={
            "select": "id,nombre_proyecto,enlace,fuente,id_publicacion,texto_completo",
            "order": "id.asc",
            "limit": "200"
        }
    )
    if respuesta.status_code != 200:
        print(f"⚠️ Error obteniendo registros: {respuesta.status_code}")
        return []
    return respuesta.json()


def actualizar_registro(db: SupabaseClient, id_registro: int, datos: dict) -> bool:
    """Actualiza un registro existente en Supabase con los datos enriquecidos."""
    campos_actualizables = [
        "tipo_tramite", "tecnologia", "nombre_proyecto", "empresa_promotora",
        "potencia_mw", "provincias", "municipios", "comunidades_autonomas",
        "estado_administrativo", "organismo_publicador", "relevante_renovables",
        "resumen", "fecha_solicitud", "fecha_resolucion", "texto_completo"
    ]
    payload = {k: v for k, v in datos.items() if k in campos_actualizables}

    respuesta = requests.patch(
        f"{db.url}/rest/v1/proyectos",
        headers={**db.headers, "Prefer": "return=minimal"},
        params={"id": f"eq.{id_registro}"},
        json=payload
    )
    return respuesta.status_code in [200, 201, 204]


def extraer_texto_segun_fuente(
    registro: dict,
    boe_scraper: BOEScraper
) -> str:
    """
    Extrae el texto completo según la fuente del registro.
    - BOE: descarga y lee el PDF
    - BOCYL/DOE/otros: ya tienen texto_completo guardado, lo reutilizamos
    """
    fuente = registro.get("fuente", "")
    enlace = registro.get("enlace", "")
    id_pub = registro.get("id_publicacion", "")
    texto_actual = registro.get("texto_completo", "") or ""

    # Si ya tiene texto largo (BOCYL/DOE), lo reutilizamos directamente
    if len(texto_actual) > 200 and fuente != "BOE":
        return texto_actual

    # Para BOE o registros con texto corto: descargamos el PDF
    if enlace and enlace.endswith(".pdf"):
        texto_pdf = boe_scraper.extraer_texto_pdf(enlace, id_pub)
        if texto_pdf and len(texto_pdf) > 100:
            return texto_pdf

    # Fallback: usar el texto actual o el título
    return texto_actual or registro.get("nombre_proyecto", "")


def main():
    print("\n🔄 Reprocesamiento de registros existentes — TramitaRenova\n")

    # Inicializar componentes
    db = SupabaseClient()
    classifier = Classifier()
    boe_scraper = BOEScraper()

    # Obtener todos los registros
    registros = obtener_todos_los_registros(db)
    if not registros:
        print("⚠️ No se encontraron registros en Supabase.")
        return

    total = len(registros)
    print(f"📋 Registros a reprocesar: {total}\n")

    actualizados = 0
    errores = 0
    omitidos = 0

    for i, registro in enumerate(registros, 1):
        id_reg = registro["id"]
        nombre = registro.get("nombre_proyecto", f"ID {id_reg}")
        fuente = registro.get("fuente", "?")

        print(f"[{i}/{total}] {fuente} — {nombre[:60]}")

        try:
            # Extraer texto completo
            texto = extraer_texto_segun_fuente(registro, boe_scraper)

            if not texto or len(texto) < 50:
                print(f"  ⏭️ Sin texto suficiente, omitido")
                omitidos += 1
                continue

            # Reclasificar con Haiku
            datos = classifier.clasificar({
                "titulo": nombre,
                "texto_completo": texto,
                "enlace": registro.get("enlace", ""),
                "fuente": fuente,
                "id_publicacion": registro.get("id_publicacion", "")
            })

            if not datos:
                print(f"  ⏭️ Haiku devolvió None (no relevante), omitido")
                omitidos += 1
                continue

            # Actualizar en Supabase
            ok = actualizar_registro(db, id_reg, datos)
            if ok:
                municipios = datos.get("municipios") or []
                empresa = datos.get("empresa_promotora") or "—"
                fecha_res = datos.get("fecha_resolucion") or "—"
                print(f"  ✅ Actualizado — empresa: {empresa} | municipios: {len(municipios)} | fecha_res: {fecha_res}")
                actualizados += 1
            else:
                print(f"  ⚠️ Error al actualizar en Supabase")
                errores += 1

        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            errores += 1

        # Pausa entre registros para no saturar la API
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"  REPROCESAMIENTO COMPLETADO")
    print(f"{'='*50}")
    print(f"✅ Actualizados:  {actualizados}")
    print(f"⏭️  Omitidos:      {omitidos}")
    print(f"⚠️  Errores:       {errores}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
