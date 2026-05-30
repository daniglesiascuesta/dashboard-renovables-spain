import requests
from bs4 import BeautifulSoup
from datetime import date
from scrapers.base_scraper import BaseScraper


class BOJAScraper(BaseScraper):
    """
    Scraper para el Boletín Oficial de la Junta de Andalucía (BOJA).
    Web: https://www.juntadeandalucia.es/boja
    Frecuencia: diaria (lunes a viernes)
    Competencia: proyectos renovables en Andalucía

    Estrategia de scraping (dos pasos):
    1. /eboja/YYYYMMDD.html → obtiene el número de boletín del día (e.g. "2026/102/")
    2. /eboja/2026/102/     → lista de entradas individuales

    Estructura del HTML (verificada):
      <p>Título de la disposición...</p>
      <p><a href="BOJA26-102-XXXXX-XXXX-01_XXXXXXXX.pdf">PDF oficial auténtico</a></p>
      <p><a href="/boja/2026/102/1">Otros formatos</a></p>

    El <p> anterior al enlace PDF contiene el título.
    """

    BASE_URL = "https://www.juntadeandalucia.es"

    @property
    def nombre_fuente(self) -> str:
        return "BOJA"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        try:
            # Paso 1: obtener el número de boletín correspondiente a la fecha
            url_fecha = f"{self.BASE_URL}/eboja/{fecha.strftime('%Y%m%d')}.html"
            r = requests.get(url_fecha, timeout=15)
            if r.status_code != 200:
                return []

            boletin_rel = self._extraer_url_boletin(r.text, str(fecha.year))
            if not boletin_rel:
                return []

            # Paso 2: obtener las entradas del boletín
            url_boletin = f"{self.BASE_URL}/eboja/{boletin_rel}"
            r2 = requests.get(url_boletin, timeout=15)
            if r2.status_code != 200:
                return []

            return self._parsear_boletin(r2.text, boletin_rel.rstrip("/"))

        except Exception as e:
            print(f"⚠️ [BOJA] Error: {e}")
            return []

    def _extraer_url_boletin(self, html: str, anio: str) -> str:
        """Extrae la URL relativa del boletín ordinario del día (e.g. '2026/102/')."""
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Boletín ordinario: "2026/102/" — excluye complementarios (c01, c02...)
            if href.startswith(anio + "/") and "/c" not in href and href.endswith("/"):
                return href
        return ""

    def _parsear_boletin(self, html: str, boletin_path: str) -> list[dict]:
        """
        Extrae entradas individuales de la página del boletín.
        Identifica cada entrada buscando <p> que contienen solo el enlace PDF (BOJA*.pdf),
        y toma el <p> inmediatamente anterior como título.
        """
        soup = BeautifulSoup(html, "html.parser")
        publicaciones = []

        for p in soup.find_all("p"):
            a_tags = p.find_all("a", href=True)
            if len(a_tags) != 1:
                continue
            href = a_tags[0]["href"]
            if not (href.endswith(".pdf") and href.startswith("BOJA")):
                continue

            prev_p = p.find_previous_sibling("p")
            if not prev_p:
                continue
            titulo = prev_p.get_text(strip=True)
            if not titulo:
                continue

            enlace = f"{self.BASE_URL}/eboja/{boletin_path}/{href}"
            id_pub = href.replace(".pdf", "")

            publicaciones.append({
                "titulo": titulo,
                "enlace": enlace,
                "texto_completo": titulo,
                "id_publicacion": id_pub,
                "fuente": self.nombre_fuente,
            })

        return publicaciones
