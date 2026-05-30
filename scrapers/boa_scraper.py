import requests
from datetime import date
from scrapers.base_scraper import BaseScraper


class BOAScraper(BaseScraper):
    """
    Scraper para el Boletín Oficial de Aragón (BOA).
    Web: https://www.boa.aragon.es
    Frecuencia: diaria (lunes a viernes)
    Competencia: proyectos renovables en Aragón
    Relevancia: ⭐⭐⭐⭐⭐ — segunda comunidad con mayor volumen renovable de España

    Estrategia: el BOA expone el texto completo del último boletín publicado
    via BRSCGI. Cada documento tiene un código CSV único: BOA{YYYYMMDD}{seq}.
    """

    BASE_URL = "https://www.boa.aragon.es"
    SUMARIO_URL = (
        f"{BASE_URL}/cgi-bin/EBOA/BRSCGI"
        f"?CMD=VERDOC&BASE=BBOA&DOCR=1&SEC=BUSQUEDA_AVANZADA&SEPARADOR="
    )

    @property
    def nombre_fuente(self) -> str:
        return "BOA"

    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        """
        Obtiene el último BOA publicado.
        El parámetro fecha se usa para construir el id pero el BOA
        siempre devuelve el boletín más reciente disponible.
        """
        try:
            respuesta = requests.get(self.SUMARIO_URL, timeout=20)
            if respuesta.status_code != 200:
                return []

            texto = respuesta.content.decode("latin-1", errors="ignore")
            if not texto or "csv: BOA" not in texto:
                return []

            return self._parsear_texto_boletin(texto)

        except Exception as e:
            print(f"⚠️ [BOA] Error: {e}")
            return []

    def _parsear_texto_boletin(self, texto: str) -> list[dict]:
        """Divide el boletín en publicaciones individuales por código CSV."""
        publicaciones = []
        lineas = texto.split("\n")
        item_actual = []
        csv_actual = ""

        for linea in lineas:
            linea = linea.strip()

            if linea.startswith("csv: BOA") and len(linea) > 12:
                if item_actual and csv_actual:
                    pub = self._construir_publicacion(item_actual, csv_actual)
                    if pub:
                        publicaciones.append(pub)
                csv_actual = linea.replace("csv: ", "").strip()
                item_actual = []
            else:
                if linea and not linea.startswith("Depósito legal"):
                    item_actual.append(linea)

        # Último item
        if item_actual and csv_actual:
            pub = self._construir_publicacion(item_actual, csv_actual)
            if pub:
                publicaciones.append(pub)

        return publicaciones

    def _construir_publicacion(
        self, lineas: list[str], csv_code: str
    ) -> dict | None:
        """Construye el dict de publicación."""
        texto_completo = " ".join(lineas)
        if len(texto_completo) < 50:
            return None

        titulo = lineas[0] if lineas else texto_completo[:200]
        enlace = f"{self.BASE_URL}/cgi-bin/EBOA/BRSCGI?CMD=VEROBJ&MLKOB={csv_code}"

        return {
            "titulo": titulo,
            "enlace": enlace,
            "texto_completo": texto_completo,
            "id_publicacion": csv_code,
            "fuente": self.nombre_fuente,
        }