import time
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

    Estrategia de extracción:
    - Lee el sumario diario para obtener títulos e IDs
    - Pre-filtra por título con es_relevante() antes de descargar nada
    - Para las publicaciones relevantes, descarga la versión HTML
      via txt.php?id=... y extrae el cuerpo legal (div#textoxslt)
    - El campo enlace apunta siempre al PDF para uso del usuario final
    """

    BASE_URL = "https://www.boe.es"
    HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    TEXTO_MAX_CHARS = 8000
    DELAY_ENTRE_DESCARGAS = 0.3  # segundos

    @property
    def nombre_fuente(self) -> str:
        return "BOE"

    def extraer_texto_html(self, id_publicacion: str) -> str:
        """
        Descarga la versión HTML de una disposición del BOE y extrae
        el cuerpo legal limpio desde div#textoxslt.
        Devuelve cadena vacía si falla.
        """
        url = f"{self.BASE_URL}/diario_boe/txt.php?id={id_publicacion}"
        try:
            r = requests.get(url, timeout=15, headers=self.HEADERS)
            if r.status_code != 200:
                print(f"⚠️ [BOE] HTML no disponible para {id_publicacion} (status {r.status_code})")
                return ""
            soup = BeautifulSoup(r.text, "html.parser")
            contenedor = soup.find(id="textoxslt")
            if not contenedor:
                print(f"⚠️ [BOE] div#textoxslt no encontrado en {id_publicacion}")
                return ""
            texto = contenedor.get_text(separator=" ", strip=True)
            return " ".join(texto.split())[:self.TEXTO_MAX_CHARS]
        except Exception as e:
            print(f"⚠️ [BOE] Error extrayendo HTML {id_publicacion}: {e}")
            return ""

    def construir_enlace_pdf(self, fecha: date, id_publicacion: str) -> str:
        """Construye la URL al PDF para uso del usuario final."""
        fecha_path = fecha.strftime("%Y/%m/%d")
        return f"{self.BASE_URL}/boe/dias/{fecha_path}/pdfs/{id_publicacion}.pdf"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        url = f"{self.BASE_URL}/boe/dias/{fecha.strftime('%Y/%m/%d')}/"
        try:
            respuesta = requests.get(url, timeout=15, headers=self.HEADERS)
        except Exception as e:
            print(f"⚠️ [BOE] Error obteniendo sumario {fecha}: {e}")
            return []

        soup = BeautifulSoup(respuesta.text, "html.parser")
        items = soup.find_all("li", class_="dispo")
        if not items:
            return []

        publicaciones = []
        descargados = 0

        for item in items:
            titulo = item.get_text(strip=True)
            enlace_tag = item.find("a", href=True)
            if not enlace_tag:
                continue

            href = enlace_tag["href"]
            # Extraer id_publicacion del enlace (ej: /diario_boe/txt.php?id=BOE-A-2026-10653)
            id_publicacion = ""
            if "id=" in href:
                id_publicacion = href.split("id=")[-1].strip()
            elif href.endswith(".pdf"):
                id_publicacion = href.split("/")[-1].replace(".pdf", "")

            if not id_publicacion:
                continue

            enlace_pdf = self.construir_enlace_pdf(fecha, id_publicacion)

            # Pre-filtro por título: solo descargamos HTML si el título ya es relevante
            if not self.es_relevante(titulo):
                publicaciones.append({
                    "titulo": titulo,
                    "enlace": enlace_pdf,
                    "texto_completo": titulo,
                    "id_publicacion": id_publicacion,
                    "fuente": self.nombre_fuente
                })
                continue

            # Descarga HTML solo para publicaciones relevantes
            time.sleep(self.DELAY_ENTRE_DESCARGAS)
            texto_completo = self.extraer_texto_html(id_publicacion) or titulo
            descargados += 1

            publicaciones.append({
                "titulo": titulo,
                "enlace": enlace_pdf,
                "texto_completo": texto_completo,
                "id_publicacion": id_publicacion,
                "fuente": self.nombre_fuente
            })

        print(f"📄 [BOE] HTMLs descargados: {descargados} de {len(items)} publicaciones")
        return publicaciones
