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
   - "MOD" → Modificación de proyecto
   - "TIT" → Cambio de titularidad
   - "RES" → Resolución administrativa
   - "LIC" → Licencia o permiso municipal
   - "OTRO" → Cualquier otro trámite

2. tecnologia: Tecnología principal:
   - "Fotovoltaico", "Eólico", "Eólico offshore", "BESS",
   - "Hibridación", "LAT", "SET", "Termosolar", "Hidráulica", "OTRO"

3. nombre_proyecto: Nombre oficial completo del proyecto.

4. empresa_promotora: Razón social completa. null si no aparece.

5. potencia_mw: Número decimal en MW. Convierte kW dividiendo entre 1000. null si no aparece.

6. provincias: Lista de provincias afectadas con tildes correctas.

7. municipios: Lista de municipios mencionados.

8. comunidades_autonomas: Lista de comunidades autónomas afectadas, nombre oficial completo.

9. estado_administrativo:
   - "Información pública", "Autorizado", "Denegado",
   - "En tramitación", "Modificación aprobada", "Caducado"

10. organismo_publicador: Organismo que publica el anuncio.

11. relevante_renovables: true si es del sector renovable o infraestructura asociada. false si no.

12. resumen: Resumen ejecutivo en máximo 2 frases, claro y profesional, en español.

REGLAS:
- Usa siempre caracteres españoles: á, é, í, ó, ú, ñ
- Si un campo no puede determinarse con certeza, devuelve null
- No inventes datos que no aparezcan en el texto
- Las listas vacías se representan como []

Devuelve ÚNICAMENTE el JSON válido, sin texto adicional ni bloques markdown."""
