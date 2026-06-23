from __future__ import annotations

import anthropic
import json
import os


class Classifier:
    """
    Clasificador de publicaciones de boletines oficiales usando Claude Haiku.
    Recibe texto extraído de PDFs para máxima precisión en la extracción
    de municipios, razón social, potencia y fechas administrativas.
    """

    def __init__(self):
        self.cliente = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def clasificar(self, publicacion: dict) -> dict | None:
        """
        Recibe una publicación y devuelve los datos estructurados.
        Devuelve None si no es relevante para renovables.
        """
        try:
            # Usamos el texto completo del PDF; si no existe, el título
            texto_entrada = publicacion.get("texto_completo") or publicacion.get("titulo", "")

            mensaje = self.cliente.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                messages=[{"role": "user", "content": self._prompt(texto_entrada)}]
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

    def _prompt(self, texto: str) -> str:
        return f"""Eres un experto en regulación y tramitación administrativa del sector de energías renovables en España. Analiza el siguiente texto extraído de un boletín oficial y extrae información estructurada con máxima precisión.

TEXTO DEL DOCUMENTO:
{texto}

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
   - "Fotovoltaico", "Eólico", "Eólico offshore", "BESS",
   - "Hibridación", "LAT", "SET", "Termosolar", "Hidráulica", "OTRO"

3. nombre_proyecto: Nombre oficial del proyecto.
   - Busca el nombre entre comillas «» o ""
   - Si no hay nombre oficial usa una descripción corta como "Planta solar Vilallonga del Camp"
   - NUNCA devuelvas null — siempre debe haber un nombre

4. empresa_promotora: Razón social COMPLETA exactamente como figura en el documento, incluyendo la forma jurídica (S.L., S.A., S.L.U., S.A.U.). Busca expresiones como "la empresa X ha solicitado", "a favor de X", "promovido por X". null solo si no aparece ninguna empresa.

5. potencia_mw: Potencia en MW como número decimal. Convierte kW dividiendo entre 1000. MWp/MWn/MWac/MWdc se expresan en MW. Si hay varias, usa la potencia instalada. null si no aparece.

6. provincias: Lista de TODAS las provincias afectadas, con tildes correctas.

7. municipios: Lista COMPLETA de TODOS los municipios mencionados en el documento, con tildes correctas. Es habitual que un proyecto afecte a varios municipios (planta + línea de evacuación). Extrae todos, no solo el principal.

8. comunidades_autonomas: Lista de comunidades autónomas afectadas, nombre oficial completo.

9. estado_administrativo:
   - "Información pública", "Autorizado", "Denegado",
   - "En tramitación", "Modificación aprobada", "Caducado"

10. organismo_publicador: Organismo que publica el anuncio.

11. relevante_renovables: true si es del sector renovable o infraestructura eléctrica asociada. false si trata principalmente de gasoducto, gas natural, biometano, nuclear, carbón, infraestructura ferroviaria/viaria, o si es un anuncio de licitación o formalización de contratos públicos (no un trámite de autorización de proyecto).

12. resumen: Resumen ejecutivo en exactamente 2 frases, profesional y directo. Frase 1: qué trámite es y para qué proyecto. Frase 2: características principales (potencia, ubicación, empresa).

13. fecha_solicitud: Fecha en que se presentó o registró la solicitud. Busca expresiones como "con fecha X se solicitó", "solicitada el X", "en fecha X ... ha solicitado", "presentó solicitud el X". Formato YYYY-MM-DD. null si no aparece EXPLÍCITAMENTE en el texto.

14. fecha_resolucion: Fecha de la resolución administrativa. Busca "Resolución de fecha X", "dictó la Resolución", "en fecha X la directora/el director general ... dictó". Formato YYYY-MM-DD. null si no aparece EXPLÍCITAMENTE en el texto.

REGLAS CRÍTICAS:
- Usa siempre caracteres españoles correctos: á, é, í, ó, ú, ñ, ü
- nombre_proyecto NUNCA puede ser null — usa descripción si no hay nombre oficial
- municipios: extrae TODOS los que aparezcan, es la información más valiosa
- empresa_promotora: copia la razón social EXACTA, no la abrevies ni la inventes
- fechas: solo si aparecen EXPLÍCITAMENTE en el texto. NUNCA las calcules ni deduzcas.
- No inventes ningún dato que no aparezca en el texto
- Las listas vacías se representan como []

Devuelve ÚNICAMENTE el JSON válido, sin texto adicional ni bloques markdown."""
