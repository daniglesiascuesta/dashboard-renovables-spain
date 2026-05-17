import requests
from bs4 import BeautifulSoup
from datetime import date
from scrapers.base_scraper import BaseScraper


class BOEScraper(BaseScraper):
    """
    Scraper para el Boletín Oficial del Estado (BOE).
    Web: https://www.boe.es
    Frecuencia: diaria (lunes a sábado)
    Competencia: proyectos de ámbito estatal o pluriautonómico
    """

    BASE_URL = "https://www.boe.es"

    @property
    def nombre_fuente(self) -> str:
        return "BOE"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        url = f"{self.BASE_URL}/boe/dias/{fecha.strftime('%Y/%m/%d')}/"
        respuesta = requests.get(url, timeout=15)
        soup = BeautifulSoup(respuesta.text, "html.parser")
        items = soup.find_all("li", class_="dispo")

        if not items:
            return []

        publicaciones = []
        for item in items:
            titulo = item.get_text(strip=True)
            enlace_tag = item.find("a", href=True)
            enlace = self.BASE_URL + enlace_tag["href"] if enlace_tag else ""

            # Extraer ID de publicación del enlace
            id_pub = ""
            if enlace:
                id_pub = enlace.split("/")[-1].replace(".pdf", "")

            publicaciones.append({
                "titulo": titulo,
                "enlace": enlace,
                "texto_completo": titulo,  # En BOE el título ya es descriptivo
                "id_publicacion": id_pub,
                "fuente": self.nombre_fuente
            })

        return publicaciones
