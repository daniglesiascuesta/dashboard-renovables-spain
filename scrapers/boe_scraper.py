import io
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
    - Lee el sumario diario y obtiene título + enlace de cada publicación
    - Pre-filtra por título (keywords de inclusión/exclusión) para no
      descargar PDFs irrelevantes
    - Descarga y extrae el texto de las primeras 3 páginas del PDF de las
      publicaciones que superan el pre-filtro, para dar a Claude Haiku
      el contexto completo del documento
    """

    BASE_URL = "https://www.boe.es"

    @property
    def nombre_fuente(self) -> str:
        return "BOE"

    def extraer_texto_pdf(self, enlace: str, id_pub: str) -> str:
        """
        Descarga el PDF y extrae el texto de las primeras 3 páginas.
        Devuelve el texto limpio truncado a 3000 caracteres.
        Si falla, devuelve cadena vacía (el caller usará el título como fallback).
        """
        try:
            import pdfplumber
            respuesta = requests.get(enlace, timeout=20)
            if respuesta.status_code != 200:
                return ""
            with pdfplumber.open(io.BytesIO(respuesta.content)) as pdf:
                texto = ""
                for page in pdf.pages[:3]:
                    texto += page.extract_text() or ""
            return " ".join(texto.split())[:3000]
        except Exception as e:
            print(f"⚠️ [BOE] Error extrayendo PDF {id_pub}: {e}")
            return ""

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        url = f"{self.BASE_URL}/boe/dias/{fecha.strftime('%Y/%m/%d')}/"
        respuesta = requests.get(url, timeout=15)
        soup = BeautifulSoup(respuesta.text, "html.parser")
        items = soup.find_all("li", class_="dispo")

        if not items:
            return []

        publicaciones = []
        descargados = 0
        for item in items:
            titulo = item.get_text(strip=True)
            enlace_tag = item.find("a", href=True)
            enlace = self.BASE_URL + enlace_tag["href"] if enlace_tag else ""

            id_pub = ""
            if enlace:
                id_pub = enlace.split("/")[-1].replace(".pdf", "")

            # Pre-filtro por título: solo descargamos el PDF si el título
            # ya parece relevante. Ahorra cientos de descargas innecesarias.
            texto_completo = titulo
            if enlace.endswith(".pdf") and self.es_relevante(titulo):
                texto_pdf = self.extraer_texto_pdf(enlace, id_pub)
                if texto_pdf:
                    texto_completo = texto_pdf
                    descargados += 1

            publicaciones.append({
                "titulo": titulo,
                "enlace": enlace,
                "texto_completo": texto_completo,
                "id_publicacion": id_pub,
                "fuente": self.nombre_fuente
            })

        print(f"📄 [BOE] PDFs descargados y extraídos: {descargados}")
        return publicaciones
