from __future__ import annotations

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

    Estrategia de scraping (tres pasos):
    1. /eboja/YYYYMMDD.html → número de boletín del día (e.g. "2026/102/")
    2. /boja/YYYY/NNN/      → lista de entradas individuales (/boja/2026/102/1 ... /N)
    3. /boja/YYYY/NNN/N     → texto completo + enlace PDF de cada entrada

    Estructura verificada de /boja/YYYY/NNN/:
      <a href="/boja/2026/102/1">...</a>  (una por entrada)

    Estructura verificada de /boja/YYYY/NNN/N:
      <p>Título de la disposición...</p>
      <p>Atención: El texto que se muestra...</p>  ← ignorar
      <p>Cuerpo de la disposición...</p>
      <a href="BOJA26-102-XXXXX-XXXX-01_XXXXXXXX.pdf">Descargar PDF</a>
    """

    BASE_URL = "https://www.juntadeandalucia.es"

    @property
    def nombre_fuente(self) -> str:
        return "BOJA"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        try:
            # Paso 1: número de boletín del día
            url_fecha = f"{self.BASE_URL}/eboja/{fecha.strftime('%Y%m%d')}.html"
            r = requests.get(url_fecha, timeout=15)
            if r.status_code != 200:
                return []

            boletin_num = self._extraer_numero_boletin(r.text, str(fecha.year))
            if not boletin_num:
                return []

            # Paso 2: lista de entradas del boletín
            url_indice = f"{self.BASE_URL}/boja/{boletin_num}/"
            r2 = requests.get(url_indice, timeout=15)
            if r2.status_code != 200:
                return []

            entry_urls = self._extraer_entradas(r2.text, boletin_num)
            if not entry_urls:
                return []

            # Paso 3: contenido de cada entrada individual
            publicaciones = []
            for url_entrada in entry_urls:
                pub = self._parsear_entrada(url_entrada, boletin_num)
                if pub:
                    publicaciones.append(pub)

            return publicaciones

        except Exception as e:
            print(f"⚠️ [BOJA] Error: {e}")
            return []

    def _extraer_numero_boletin(self, html: str, anio: str) -> str:
        """Devuelve el path del boletín ordinario, e.g. '2026/102'."""
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Boletín ordinario: "2026/102/" — excluye complementarios (c01, c02…)
            if href.startswith(anio + "/") and "/c" not in href and href.endswith("/"):
                return href.rstrip("/")
        return ""

    def _extraer_entradas(self, html: str, boletin_num: str) -> list[str]:
        """Devuelve lista de URLs absolutas a las entradas individuales."""
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        prefix = f"/boja/{boletin_num}/"
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith(prefix) and href[len(prefix):].isdigit():
                urls.append(f"{self.BASE_URL}{href}")
        return urls

    def _parsear_entrada(self, url: str, boletin_num: str) -> dict | None:
        """Fetches una entrada individual y extrae título, texto y PDF."""
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                return None

            soup = BeautifulSoup(r.text, "html.parser")

            # Párrafos con contenido real (excluye el disclaimer "Atención:")
            parrafos = [
                p.get_text(strip=True)
                for p in soup.find_all("p")
                if len(p.get_text(strip=True)) > 30
                and not p.get_text(strip=True).startswith("Atención:")
            ]
            if not parrafos:
                return None

            titulo = parrafos[0]
            texto_completo = " ".join(parrafos)

            # Enlace PDF: href empieza por "BOJA" y termina en ".pdf"
            pdf_link = next(
                (a["href"] for a in soup.find_all("a", href=True)
                 if a["href"].startswith("BOJA") and a["href"].endswith(".pdf")),
                None
            )
            if not pdf_link:
                return None

            enlace = f"{self.BASE_URL}/boja/{boletin_num}/{pdf_link}"
            id_pub = pdf_link.replace(".pdf", "")

            return {
                "titulo": titulo,
                "enlace": enlace,
                "texto_completo": texto_completo,
                "id_publicacion": id_pub,
                "fuente": self.nombre_fuente,
            }

        except Exception as e:
            print(f"⚠️ [BOJA] Error en entrada {url}: {e}")
            return None
