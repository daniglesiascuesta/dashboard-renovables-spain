import requests
from bs4 import BeautifulSoup
from datetime import date
from scrapers.base_scraper import BaseScraper


class DOEScraper(BaseScraper):
    """
    Scraper para el Diario Oficial de Extremadura (DOE).
    Web: http://doe.juntaex.es
    Frecuencia: diaria (lunes a viernes)
    Competencia: proyectos renovables en Extremadura

    Estrategia de scraping:
    URL: /ultimosdoe/mostrardoe.php?fecha=YYYYMMDD&t=o

    Estructura del HTML (verificada):
    - Secciones marcadas con <h3> (e.g. "II. AUTORIDADES Y PERSONAL")
    - Entradas como texto plano sin wrapper semántico
    - Cada entrada tiene un enlace PDF: href="/pdfs/doe/YYYY/ISSUEo/DOCID.pdf"
    - El título es el texto del elemento padre, excluyendo los textos de los enlaces
    - ID de publicación: nombre del fichero PDF sin extensión (e.g. "26061304")
    """

    BASE_URL = "http://doe.juntaex.es"

    @property
    def nombre_fuente(self) -> str:
        return "DOE"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        try:
            url = f"{self.BASE_URL}/ultimosdoe/mostrardoe.php?fecha={fecha.strftime('%Y%m%d')}&t=o"
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                return []

            return self._parsear_boletin(r.text)

        except Exception as e:
            print(f"⚠️ [DOE] Error: {e}")
            return []

    def _parsear_boletin(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        publicaciones = []
        vistos = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/pdfs/doe/" not in href:
                continue

            id_pub = href.split("/")[-1].replace(".pdf", "")
            if id_pub in vistos:
                continue
            vistos.add(id_pub)

            # Título: texto del elemento padre sin los textos de sus enlaces
            parent = link.parent
            titulo = parent.get_text(separator=" ", strip=True)
            for a in parent.find_all("a"):
                titulo = titulo.replace(a.get_text(strip=True), "")
            titulo = " ".join(titulo.split()).strip()

            if not titulo or len(titulo) < 10:
                continue

            enlace = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            publicaciones.append({
                "titulo": titulo,
                "enlace": enlace,
                "texto_completo": titulo,
                "id_publicacion": id_pub,
                "fuente": self.nombre_fuente,
            })

        return publicaciones
