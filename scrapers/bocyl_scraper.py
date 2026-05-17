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

        # El BOCYL estructura sus items en divs con clase 'itemSumario'
        items = soup.find_all("div", class_="itemSumario")

        if not items:
            # Intento alternativo con estructura de lista
            items = soup.find_all("li", class_="sumario")

        if not items:
            return []

        publicaciones = []
        for item in items:
            titulo = item.get_text(strip=True)
            enlace_tag = item.find("a", href=True)

            if not enlace_tag:
                continue

            href = enlace_tag["href"]
            enlace = href if href.startswith("http") else self.BASE_URL + href
            id_pub = href.split("=")[-1] if "=" in href else ""

            publicaciones.append({
                "titulo": titulo,
                "enlace": enlace,
                "texto_completo": titulo,
                "id_publicacion": f"BOCYL-{id_pub}",
                "fuente": self.nombre_fuente
            })

        return publicaciones
