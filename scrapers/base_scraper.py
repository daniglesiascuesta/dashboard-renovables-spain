from abc import ABC, abstractmethod
from datetime import date, timedelta
import requests
from bs4 import BeautifulSoup


class BaseScraper(ABC):
    """
    Clase base para todos los scrapers de boletines oficiales españoles.
    Cada fuente hereda de esta clase e implementa sus métodos específicos.
    Arquitectura modular y escalable para incorporar nuevos boletines.
    """

    # ── INCLUSIONES ────────────────────────────────────────────────────────────
    # Términos que identifican publicaciones relevantes para el sector renovable
    KEYWORDS = [
        # Tecnologías de generación
        "fotovoltaic", "fotovoltaica", "solar fotovoltaic",
        "planta solar", "parque solar", "instalación solar",
        "eólico", "eólica", "parque eólico", "aerogenerador",
        "turbina eólica", "energía eólica", "offshore", "onshore",
        "termosolar", "solar termoeléctric", "concentración solar",

        # Almacenamiento
        "almacenamiento", "bess", "batería", "baterías",
        "acumulación energética", "sistema de almacenamiento",

        # Hibridación
        "hibridación", "híbrido", "hibrida", "hibridado",

        # Infraestructura de evacuación
        "evacuación", "línea de alta tensión", "línea alta tensión",
        "subestación eléctrica", "subestación transformadora",
        "centro de seccionamiento", "punto de conexión",
        "infraestructura de evacuación", "línea de evacuación",

        # Trámites administrativos del sector
        "autorización administrativa previa",
        "autorización administrativa de construcción",
        "autorización administrativa de explotación",
        "declaración de impacto ambiental",
        "declaración de utilidad pública",
        "información pública",
        "autoconsumo colectivo", "autoconsumo industrial",

        # Términos generales del sector
        "energía renovable", "generación renovable",
        "instalación de producción de energía eléctrica",
        "industria y energía",
    ]

    # ── EXCLUSIONES ────────────────────────────────────────────────────────────
    # Términos que descartan publicaciones aunque contengan keywords de inclusión
    KEYWORDS_EXCLUSION = [
        # Gas y combustibles fósiles
        "gasoducto", "gas natural", "gas licuado", "gnl", "glp",
        "biometano", "metano", "propano", "butano",
        "oleoducto", "oleoducto", "combustible fósil",
        "central de ciclo combinado", "ciclo combinado",
        "renovación de la canalización",

        # Nuclear
        "nuclear", "central nuclear", "uranio", "fisión",

        # Carbón y térmica convencional
        "central térmica", "térmica convencional",
        "carbón", "hulla", "antracita",

        # Infraestructuras no energéticas
        "carretera", "autopista", "autovía", "ferroviaria",
        "ferrocarril", "alta velocidad", "saneamiento",
        "abastecimiento de agua", "residuos urbanos",

        # Agua y concesiones no energéticas
        "concesión de aguas", "aprovechamiento de aguas",
        "aguas superficiales", "aguas subterráneas",
        "caudal ecológico", "perímetro de protección",
        "dominio público hidráulico",

        # Red de distribución de baja y media tensión no asociada a renovables
        "13,2 kv", "13.2 kv", "15 kv", "20 kv",
        "red de distribución", "electrificación de",
        "naves industrial", "granja", "polígono industrial",
        "alumbrado", "suministro eléctrico",
    ]

    @property
    @abstractmethod
    def nombre_fuente(self) -> str:
        """Nombre identificador de la fuente. Ej: 'BOE', 'BOCYL', 'BOA'"""
        pass

    @abstractmethod
    def obtener_publicaciones(self, fecha: date) -> list[dict]:
        """
        Obtiene todas las publicaciones de una fecha concreta.
        Devuelve lista de dicts con: titulo, enlace, texto_completo, id_publicacion, fuente
        """
        pass

    def es_relevante(self, titulo: str, texto_completo: str = "") -> bool:
        """
        Determina si una publicación es relevante para el sector renovable.
        Analiza tanto el título como el texto completo para mayor precisión.
        Una publicación es relevante si contiene keywords de inclusión
        y NO contiene keywords de exclusión en ninguna de las dos fuentes.
        """
        texto_analisis = f"{titulo} {texto_completo}".lower()
        titulo_lower = titulo.lower()

        # Verificar exclusiones — si aparecen en título o texto, descartamos
        for kw in self.KEYWORDS_EXCLUSION:
            if kw in texto_analisis:
                return False

        # Verificar inclusiones — al menos una debe estar presente en el título
        tiene_keyword_titulo = any(kw in titulo_lower for kw in self.KEYWORDS)
        return tiene_keyword_titulo

    def obtener_con_reintento(self, dias_atras: int = 5) -> tuple[list[dict], date]:
        """
        Intenta obtener publicaciones de hoy.
        Si no hay boletín (fin de semana, festivo), retrocede hasta dias_atras días.
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
        """
        Filtra las publicaciones relevantes para renovables.
        Usa tanto el título como el texto completo para mayor precisión.
        """
        relevantes = [
            p for p in publicaciones
            if self.es_relevante(
                p.get("titulo", ""),
                p.get("texto_completo", "")
            )
        ]
        print(f"✅ [{self.nombre_fuente}] Relevantes: {len(relevantes)} de {len(publicaciones)}")
        return relevantes