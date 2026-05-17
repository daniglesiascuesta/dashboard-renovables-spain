"""
Dashboard Renovables España
Orquestador principal del pipeline de inteligencia regulatoria.

Fuentes activas:
- BOE (Boletín Oficial del Estado)
- BOCYL (Boletín Oficial de Castilla y León)

Ejecución: diaria automática via GitHub Actions (lunes a viernes 13:00h)
"""

from scrapers.boe_scraper import BOEScraper
from scrapers.bocyl_scraper import BOCYLScraper
from processor.classifier import Classifier
from database.supabase_client import SupabaseClient


def procesar_fuente(scraper, classifier, db):
    """Ejecuta el pipeline completo para una fuente concreta."""
    print(f"\n{'='*50}")
    print(f"  Procesando: {scraper.nombre_fuente}")
    print(f"{'='*50}")

    # 1. Obtener publicaciones
    publicaciones, fecha = scraper.obtener_con_reintento()
    if not publicaciones:
        print(f"⚠️ Sin publicaciones para {scraper.nombre_fuente}")
        return {"guardados": 0, "duplicados": 0, "errores": 0}

    # 2. Filtrar relevantes
    relevantes = scraper.filtrar_relevantes(publicaciones)
    if not relevantes:
        print(f"ℹ️ Sin publicaciones relevantes en {scraper.nombre_fuente}")
        return {"guardados": 0, "duplicados": 0, "errores": 0}

    # 3. Clasificar con Claude y guardar
    proyectos = []
    for pub in relevantes:
        datos = classifier.clasificar(pub)
        if datos:
            datos["fecha_publicacion"] = str(fecha)
            proyectos.append(datos)

    # 4. Guardar en Supabase
    stats = db.guardar_proyectos(proyectos)
    print(f"📊 {scraper.nombre_fuente} — Guardados: {stats['guardados']} | Duplicados: {stats['duplicados']} | Errores: {stats['errores']}")
    return stats


def main():
    print("\n🌱 Dashboard Renovables España — Iniciando pipeline\n")

    # Inicializar componentes
    classifier = Classifier()
    db = SupabaseClient()

    # Fuentes activas — añadir nuevas fuentes aquí
    fuentes = [
        BOEScraper(),
        BOCYLScraper(),
    ]

    # Procesar cada fuente
    total = {"guardados": 0, "duplicados": 0, "errores": 0}
    for scraper in fuentes:
        stats = procesar_fuente(scraper, classifier, db)
        for k in total:
            total[k] += stats[k]

    # Resumen final
    print(f"\n{'='*50}")
    print(f"  RESUMEN FINAL")
    print(f"{'='*50}")
    print(f"✅ Total guardados:   {total['guardados']}")
    print(f"⏭️  Total duplicados:  {total['duplicados']}")
    print(f"⚠️  Total errores:     {total['errores']}")
    print(f"\n🏁 Pipeline completado\n")


if __name__ == "__main__":
    main()
