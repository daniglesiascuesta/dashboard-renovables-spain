from abc import ABC, abstractmethod
from datetime import date, timedelta
import requests
from bs4 import BeautifulSoup


class BaseScraper(ABC):
    """
    Clase base para todos los scrapers de boletines oficiales.
    Cada nuevo boletín hereda de esta clase e implementa sus métodos.
    """

    KEYWORDS = [
        "fotovoltaic", "solar", "eólico", "eólica",
        "almacenamiento", "bess", "batería", "renovable",
        "evacuación", "subestación", "hibridación",
        "parque eólico", "planta solar", "autorización ambiental",
        "declaración impacto", "utilidad pública",
        "generación eléctrica", "industria y energía",
        "aerogenerador", "autoconsumo"
    ]

    KEYWORDS_EXCLUSION = [
        "gasoducto",
        "biometano",
        "gas natural",
        "oleoducto",
        "nuclear",
        "carbón",
        "térmica convencional"
    ]

    @property
    @abstractmethod
    def nombre_fuente(self) -> str:
        """Nombre identificador de la fuente. Ej: 'BOE', 'BOCYL'"""
        pass

    @abstractmethod
    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        """
        Obtiene todas las publicaciones de una fecha concreta.
        Devuelve lista de dicts con: titulo, enlace, texto_completo, id_publicacion
        """
        pass

    def es_relevante(self, texto: str) -> bool:
        """Filtra si una publicación es relevante para el sector renovable."""
        texto_lower = texto.lower()
        tiene_keyword = any(kw in texto_lower for kw in self.KEYWORDS)
        tiene_exclusion = any(kw in texto_lower for kw in self.KEYWORDS_EXCLUSION)
        return tiene_keyword and not tiene_exclusion

    def obtener_con_reintento(self, dias_atras: int = 5) -> tuple[list[dict], date]:
        """
        Intenta obtener publicaciones de hoy.
        Si no hay boletín (fin de semana, festivo), retrocede hasta 5 días.
        """
        for i in range(dias_atras):
            fecha = date.today() - timedelta(days=i)
            try:
                publicaciones = self.obtener_publicaciones(fecha)
                if publicaciones:
                    print(f"✅ [{self.nombre_fuente}] Boletín encontrado: {fecha} — {len(publicaciones)} publicaciones")
                    return publicaciones, fecha
            except Exception as e:
                print(f"⚠️ [{self.nombre_fuente}] Error en fecha {fecha}: {e}")
                continue

        print(f"⚠️ [{self.nombre_fuente}] No se encontró boletín en los últimos {dias_atras} días")
        return [], date.today()

    def filtrar_relevantes(self, publicaciones: list[dict]) -> list[dict]:
        """Filtra solo las publicaciones relevantes para renovables."""
        relevantes = [p for p in publicaciones if self.es_relevante(p.get("titulo", ""))]
        print(f"✅ [{self.nombre_fuente}] Relevantes: {len(relevantes)} de {len(publicaciones)}")
        return relevantes