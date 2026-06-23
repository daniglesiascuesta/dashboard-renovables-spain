from scrapers.boe_scraper import BOEScraper
from processor.classifier import Classifier

# Documento real de prueba: planta solar "La Selva" 4,99 MW, Abda Energía S.L.
# Publicado en BOE el 27/05/2026, sección V-B, página 27507
ENLACE_PDF = "https://www.boe.es/boe/dias/2026/05/27/pdfs/BOE-B-2026-17410.pdf"

scraper = BOEScraper()
print("=== EXTRACCIÓN DE TEXTO DEL PDF ===")
texto = scraper.extraer_texto_pdf(ENLACE_PDF, "BOE-B-2026-17410")
print(texto[:1500])
print("\n=== LONGITUD TOTAL ===")
print(f"{len(texto)} caracteres")

print("\n=== CLASIFICACIÓN CON HAIKU ===")
classifier = Classifier()
resultado = classifier.clasificar({
    "titulo": "Anuncio planta solar La Selva",
    "texto_completo": texto,
    "enlace": ENLACE_PDF,
    "fuente": "BOE",
    "id_publicacion": "BOE-B-2026-17410"
})

import json
print(json.dumps(resultado, indent=2, ensure_ascii=False))
