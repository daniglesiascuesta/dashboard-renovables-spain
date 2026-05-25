import anthropic
import json
import os


class Classifier:
    """
    Clasificador de publicaciones de boletines oficiales usando Claude.
    Extrae información estructurada de trámites administrativos renovables.
    """

    def __init__(self):
        self.cliente = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def clasificar(self, publicacion: dict) -> dict | None:
        """
        Recibe una publicación y devuelve los datos estructurados.
        Devuelve None si no es relevante para renovables.
        """
        try:
            mensaje = self.cliente.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": self._prompt(publicacion["titulo"])}]
            )

            texto = mensaje.content[0].text.strip()
            texto = texto.removeprefix("```json").removesuffix("```").strip()
            datos = json.loads(texto)

            if not datos.get("relevante_renovables", False):
                return None

            datos["enlace"] = publicacion.get("enlace", "")
            datos["fuente"] = publicacion.get("fuente", "")
            datos["id_publicacion"] = publicacion.get("id_publicacion", "")
            datos["texto_completo"] = publicacion.get("texto_completo", "")

            return json.loads(json.dumps(datos, ensure_ascii=False))

        except Exception as e:
            print(f"⚠️ Error clasificando: {e}")
            return None

    def _prompt(self, titulo: str) -> str:
        return f"""Eres un experto en regulación y tramitación administrativa del sector de energías renovables en España. Tu tarea es analizar publicaciones de boletines oficiales y extraer información estructurada con máxima precisión.

TEXTO DEL BOLETÍN:
{titulo}

INSTRUCCIONES DE EXTRACCIÓN:

1. tipo_tramite: Identifica el tipo de trámite usando EXCLUSIVAMENTE estos códigos:
   - "AAP" → Autorización Administrativa Previa
   - "AAC" → Autorización Administrativa de Construcción
   - "AAE" → Autorización Administrativa de Explotación
   - "DIA" → Declaración de Impacto Ambiental
   - "DUP" → Declaración de Utilidad Pública
   - "IP" → Información Pública
   - "AAP+DIA" → Tramitación conjunta AAP y DIA
   - "AAP+AAC" → Tramitación conjunta AAP y AAC
   - "AAP+DUP" → Tramitación conjunta AAP y DUP
   - "MOD" → Modificación de proyecto
   - "TIT" → Cambio de titularidad
   - "RES" → Resolución administrativa o expropiación
   - "LIC" → Licencia o permiso municipal
   - "OTRO" → Cualquier otro trámite

2. tecnologia: Tecnología principal del proyecto:
   - "Fotovoltaico" → plantas solares fotovoltaicas
   - "Eólico" → parques eólicos onshore
   - "Eólico offshore" → parques eólicos marinos
   - "BESS" → sistemas de almacenamiento por batería
   - "Hibridación" → proyectos que combinan tecnologías
   - "LAT" → línea de alta tensión o infraestructura de evacuación
   - "SET" → subestación eléctrica transformadora
   - "Termosolar" → plantas termosolares
   - "Hidráulica" → centrales hidroeléctricas
   - "OTRO" → tecnología no identificada claramente

3. nombre_proyecto: Nombre oficial del proyecto.
   - Busca el nombre entre comillas «» o entre comillas normales ""
   - Si no hay nombre oficial usa una descripción corta y descriptiva como "Planta solar Palencia" o "Parque eólico León"
   - NUNCA devuelvas null — siempre debe haber un nombre

4. empresa_promotora: Razón social completa incluyendo forma jurídica (SL, SAU, SA, SLU...).
   - Si aparecen varias empresas, incluye la promotora principal
   - null solo si no aparece ninguna empresa en el texto

5. potencia_mw: Potencia en MW como número decimal.
   - Convierte kW a MW dividiendo entre 1000
   - MWp, MWn, MWac, MWdc → todos se expresan en MW
   - Si hay varias potencias (instalada + evacuación), usa la potencia instalada
   - null solo si no aparece ninguna potencia en el texto

6. provincias: Lista de todas las provincias afectadas con tildes correctas.
   - Ejemplo: ["Palencia", "Burgos", "León"]

7. municipios: Lista de todos los municipios mencionados.
   - Ejemplo: ["Villamediana", "Tordesillas"]

8. comunidades_autonomas: Lista de comunidades autónomas afectadas, nombre oficial completo.
   - Ejemplo: ["Castilla y León", "Cataluña"]

9. estado_administrativo:
   - "Información pública" → en fase de exposición pública
   - "Autorizado" → resolución favorable emitida
   - "Denegado" → resolución desfavorable
   - "En tramitación" → proceso en curso sin resolución final
   - "Modificación aprobada" → modificación de proyecto aprobada
   - "Caducado" → expediente caducado o archivado

10. organismo_publicador: Organismo que publica el anuncio.
    - Ejemplo: "Dirección General de Política Energética y Minas"
    - Ejemplo: "Servicio Territorial de Industria de León"

11. relevante_renovables: 
    - true → proyecto claramente del sector renovable o infraestructura eléctrica asociada
    - false → si el texto trata principalmente de gasoductos, gas natural, biometano, nuclear, carbón o infraestructuras no energéticas

12. resumen: Resumen ejecutivo en exactamente 2 frases, profesional y directo.
    - Frase 1: qué trámite es y para qué proyecto
    - Frase 2: características principales (potencia, ubicación, empresa si aparece)

REGLAS CRÍTICAS:
- Usa siempre caracteres españoles correctos: á, é, í, ó, ú, ñ, ü
- nombre_proyecto NUNCA puede ser null — usa descripción si no hay nombre oficial
- Si el texto menciona principalmente gasoducto, biometano o gas natural → relevante_renovables: false
- No inventes datos que no aparezcan explícitamente en el texto
- Las listas vacías se representan como []

Devuelve ÚNICAMENTE el JSON válido, sin texto adicional ni bloques markdown."""