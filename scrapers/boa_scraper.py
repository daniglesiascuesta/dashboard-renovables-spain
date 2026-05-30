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

    Estrategia de scraping:
    - El BOA expone el texto completo del boletín via BRSCGI
    - Cada documento tiene un código CSV único: BOA{YYYYMMDD}{seq}
    - Dividimos el texto por estos códigos para obtener items individuales
    """

    BASE_URL = "https://www.boa.aragon.es"

    @property
    def nombre_fuente(self) -> str:
        return "BOA"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        fecha_str = fecha.strftime("%d/%m/%Y")
        fecha_codigo = fecha.strftime("%Y%m%d")

        url = (
            f"{self.BASE_URL}/cgi-bin/EBOA/BRSCGI"
            f"?CMD=VERDOC&BASE=BBOA&DOCR=1"
            f"&SEC=BUSQUEDA_AVANZADA&SEPARADOR=&FECHA={fecha_str}"
        )

        try:
            respuesta = requests.get(url, timeout=20)
            if respuesta.status_code != 200:
                return []
        except Exception as e:
            print(f"⚠️ [BOA] Error de conexión: {e}")
            return []

        texto = respuesta.content.decode("latin-1", errors="ignore")
        if not texto or fecha_codigo not in texto:
            return []

        return self._parsear_texto_boletin(texto, fecha_codigo)

    def _parsear_texto_boletin(self, texto: str, fecha_codigo: str) -> list[dict]:
        """
        Divide el texto del boletín en publicaciones individuales
        usando los códigos CSV como separadores.
        """
        publicaciones = []
        lineas = texto.split("\n")
        item_actual = []
        csv_actual = ""

        for linea in lineas:
            linea = linea.strip()

            # Detectamos inicio de nuevo item por su código CSV
            if linea.startswith(f"csv: {fecha_codigo}"):
                # Guardamos el item anterior si tiene contenido
                if item_actual and csv_actual:
                    pub = self._construir_publicacion(item_actual, csv_actual, fecha_codigo)
                    if pub:
                        publicaciones.append(pub)

                csv_actual = linea.replace("csv: ", "").strip()
                item_actual = []
            else:
                if linea:
                    item_actual.append(linea)

        # Último item
        if item_actual and csv_actual:
            pub = self._construir_publicacion(item_actual, csv_actual, fecha_codigo)
            if pub:
                publicaciones.append(pub)

        return publicaciones

    def _construir_publicacion(
        self, lineas: list[str], csv_code: str, fecha_codigo: str
    ) -> dict | None:
        """Construye el dict de publicación a partir de las líneas de texto."""
        texto_completo = " ".join(lineas)

        # Ignoramos items demasiado cortos o sin contenido real
        if len(texto_completo) < 50:
            return None

        # El título es la primera línea significativa
        titulo = lineas[0] if lineas else texto_completo[:200]

        enlace = (
            f"{self.BASE_URL}/cgi-bin/EBOA/BRSCGI"
            f"?CMD=VEROBJ&MLKOB={csv_code}"
        )

        return {
            "titulo": titulo,
            "enlace": enlace,
            "texto_completo": texto_completo,
            "id_publicacion": csv_code,
            "fuente": self.nombre_fuente,
        }