import re
import requests
from bs4 import BeautifulSoup
from datetime import date
from scrapers.base_scraper import BaseScraper


class DOCMScraper(BaseScraper):
    """
    Scraper para el Diario Oficial de Castilla-La Mancha (DOCM).
    Web: https://docm.jccm.es
    Frecuencia: diaria (lunes a viernes)
    Competencia: proyectos renovables en Castilla-La Mancha

    Estrategia de scraping:
    URL por fecha: /docmvo/cambiarBoletin.do?fecha=YYYYMMDD

    Estructura del HTML (verificada):
      <a href="./descargarArchivo.do?ruta=2026/05/29/pdf/2026_4101.pdf&tipo=rutaDocm">
        Presupuestos Generales. Orden 75/2026
      </a>
      <a href="./detalleDocumento.do?idDisposicion=1779861766987351003">Ver detalle</a>

    El título es el texto del enlace descargarArchivo.
    ID de publicación: extraído del parámetro ruta (e.g. "2026_4101").
    """

    BASE_URL = "https://docm.jccm.es/docmvo"

    @property
    def nombre_fuente(self) -> str:
        return "DOCM"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        try:
            url = f"{self.BASE_URL}/cambiarBoletin.do?fecha={fecha.strftime('%Y%m%d')}"
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                return []

            return self._parsear_boletin(r.text)

        except Exception as e:
            print(f"⚠️ [DOCM] Error: {e}")
            return []

    def _parsear_boletin(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        publicaciones = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "descargarArchivo.do" not in href or "rutaDocm" not in href:
                continue

            titulo = link.get_text(strip=True)
            if not titulo or len(titulo) < 10:
                continue

            # ID: "2026_4101" extraído del parámetro ruta
            match = re.search(r"/(\d{4}_\d+)\.pdf", href)
            if not match:
                continue
            id_pub = match.group(1)

            if href.startswith("./"):
                enlace = f"{self.BASE_URL}/{href[2:]}"
            elif href.startswith("http"):
                enlace = href
            else:
                enlace = f"{self.BASE_URL}/{href}"

            publicaciones.append({
                "titulo": titulo,
                "enlace": enlace,
                "texto_completo": titulo,
                "id_publicacion": id_pub,
                "fuente": self.nombre_fuente,
            })

        return publicaciones
