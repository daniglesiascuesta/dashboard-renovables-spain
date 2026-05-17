import requests
from bs4 import BeautifulSoup
from datetime import date
from scrapers.base_scraper import BaseScraper


class BOCYLScraper(BaseScraper):
    """
    Scraper para el Boletín Oficial de Castilla y León (BOCYL).
    Web: https://bocyl.jcyl.es
    Frecuencia: diaria (lunes a viernes)
    Competencia: proyectos renovables en Castilla y León
    Relevancia: ⭐⭐⭐⭐⭐ — comunidad con mayor volumen renovable de España

    Estrategia de scraping:
    - La página principal del boletín lista documentos por ID (BOCYL-D-...)
    - Cada documento tiene una versión HTML con el texto completo
    - Accedemos a cada documento individualmente para extraer título y texto
    """

    BASE_URL = "https://bocyl.jcyl.es"

    @property
    def nombre_fuente(self) -> str:
        return "BOCYL"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        fecha_str = fecha.strftime("%d/%m/%Y")
        url = f"{self.BASE_URL}/boletin.do?fechaBoletin={fecha_str}"

        respuesta = requests.get(url, timeout=15)
        if respuesta.status_code != 200:
            return []

        soup = BeautifulSoup(respuesta.text, "html.parser")

        # Obtenemos todos los enlaces a versiones HTML de documentos
        enlaces_html = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "html/" in href and href.endswith(".do"):
                enlace_completo = href if href.startswith("http") else f"{self.BASE_URL}/{href}"
                id_pub = href.split("/")[-1].replace(".do", "")
                enlaces_html.append({
                    "enlace_html": enlace_completo,
                    "enlace_pdf": enlace_completo.replace("/html/", "/pdf/").replace(".do", ".pdf").replace("html/2026", "boletines/2026"),
                    "id_publicacion": id_pub
                })

        if not enlaces_html:
            return []

        # Entramos en cada documento y extraemos el título
        publicaciones = []
        for doc in enlaces_html:
            try:
                r = requests.get(doc["enlace_html"], timeout=10)
                if r.status_code != 200:
                    continue

                s = BeautifulSoup(r.text, "html.parser")
                parrafos = [
                    p.get_text(strip=True)
                    for p in s.find_all("p")
                    if len(p.get_text(strip=True)) > 50
                ]

                if not parrafos:
                    continue

                titulo = parrafos[0]
                texto_completo = " ".join(parrafos)

                publicaciones.append({
                    "titulo": titulo,
                    "enlace": doc["enlace_pdf"],
                    "texto_completo": texto_completo,
                    "id_publicacion": doc["id_publicacion"],
                    "fuente": self.nombre_fuente
                })

            except Exception as e:
                print(f"⚠️ [BOCYL] Error leyendo documento {doc['id_publicacion']}: {e}")
                continue

        return publicaciones
