import requests
from bs4 import BeautifulSoup
from datetime import date
from scrapers.base_scraper import BaseScraper


class BOAScraper(BaseScraper):
    """
    Scraper para el Boletín Oficial de Aragón (BOA).
    Web: https://www.boa.aragon.es
    Frecuencia: diaria (lunes a viernes)
    Competencia: proyectos renovables en Aragón
    Relevancia: ⭐⭐⭐⭐⭐ — segunda comunidad con mayor volumen renovable de España
    """

    BASE_URL = "https://www.boa.aragon.es"

    @property
    def nombre_fuente(self) -> str:
        return "BOA"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        fecha_str = fecha.strftime("%d/%m/%Y")
        url = f"{self.BASE_URL}/cgi-bin/EBOA/BRSCGI?CMD=VERDOC&BASE=BBOA&DOCR=1&SEC=BUSQUEDA_AVANZADA&SEPARADOR=&FECHA={fecha_str}"

        try:
            respuesta = requests.get(url, timeout=15)
            if respuesta.status_code != 200:
                return self._intentar_url_alternativa(fecha)
        except Exception:
            return self._intentar_url_alternativa(fecha)

        soup = BeautifulSoup(respuesta.text, "html.parser")
        return self._extraer_publicaciones(soup, fecha)

    def _intentar_url_alternativa(self, fecha: date) -> list[dict]:
        """Intenta URL alternativa si la principal falla."""
        anio = fecha.strftime("%Y")
        mes = fecha.strftime("%m")
        dia = fecha.strftime("%d")
        url = f"{self.BASE_URL}/eli/es-ar/o/{anio}/{mes}/{dia}"

        try:
            respuesta = requests.get(url, timeout=15)
            if respuesta.status_code != 200:
                return []
            soup = BeautifulSoup(respuesta.text, "html.parser")
            return self._extraer_publicaciones(soup, fecha)
        except Exception:
            return []

    def _extraer_publicaciones(self, soup: BeautifulSoup, fecha: date) -> list[dict]:
        """Extrae publicaciones del HTML del BOA."""
        publicaciones = []

        # El BOA lista sus items en divs o filas de tabla
        items = soup.find_all("div", class_="sumario-item")
        if not items:
            items = soup.find_all("tr", class_=lambda c: c and "fila" in c.lower())
        if not items:
            # Búsqueda genérica de enlaces a documentos
            items = soup.find_all("a", href=lambda h: h and (".pdf" in h.lower() or "BOA" in h))

        for item in items:
            try:
                if hasattr(item, "get_text"):
                    titulo = item.get_text(strip=True)
                else:
                    titulo = str(item)

                enlace_tag = item.find("a", href=True) if hasattr(item, "find") else item
                if enlace_tag and hasattr(enlace_tag, "get"):
                    href = enlace_tag.get("href", "")
                    enlace = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                else:
                    enlace = ""

                if not titulo or len(titulo) < 20:
                    continue

                id_pub = enlace.split("/")[-1].replace(".pdf", "") if enlace else ""

                publicaciones.append({
                    "titulo": titulo[:500],
                    "enlace": enlace,
                    "texto_completo": titulo,
                    "id_publicacion": f"BOA-{id_pub}",
                    "fuente": self.nombre_fuente
                })

            except Exception:
                continue

        return publicaciones