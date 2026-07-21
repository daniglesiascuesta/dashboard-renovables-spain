import requests
import os


class SupabaseClient:
    """
    Cliente para interactuar con la base de datos Supabase.
    Gestiona todas las operaciones de lectura y escritura de proyectos renovables.
    """

    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

    def proyecto_existe(self, id_publicacion: str, fuente: str) -> bool:
        """Comprueba si un proyecto ya está guardado para evitar duplicados."""
        if not id_publicacion:
            return False
        respuesta = requests.get(
            f"{self.url}/rest/v1/proyectos",
            headers=self.headers,
            params={
                "id_publicacion": f"eq.{id_publicacion}",
                "fuente": f"eq.{fuente}",
                "select": "id"
            }
        )
        return len(respuesta.json()) > 0

    COLUMNAS_VALIDAS = {
        'fecha_publicacion', 'tipo_tramite', 'tecnologia', 'nombre_proyecto',
        'empresa_promotora', 'potencia_mw', 'provincias', 'municipios',
        'comunidades_autonomas', 'estado_administrativo', 'relevante_renovables',
        'enlace', 'fuente', 'id_publicacion', 'texto_completo',
        'organismo_publicador', 'resumen', 'administracion_competente',
        'fecha_solicitud', 'fecha_resolucion'
    }

    def guardar_proyecto(self, datos: dict) -> str:
        """
        Guarda un proyecto en Supabase.
        Devuelve "guardado", "duplicado" o "error".
        """
        if self.proyecto_existe(datos.get("id_publicacion", ""), datos.get("fuente", "")):
            print(f"⏭️ Ya existe: {datos.get('nombre_proyecto')} [{datos.get('fuente')}]")
            return "duplicado"

        datos = {k: v for k, v in datos.items() if k in self.COLUMNAS_VALIDAS}

        try:
            respuesta = requests.post(
                f"{self.url}/rest/v1/proyectos",
                headers=self.headers,
                json=datos
            )

            if respuesta.status_code in [200, 201]:
                print(f"✅ Guardado: {datos.get('nombre_proyecto')} [{datos.get('fuente')}]")
                return "guardado"
            else:
                print(f"⚠️ Error guardando [{respuesta.status_code}]: {respuesta.text[:100]}")
                return "error"
        except Exception as e:
            print(f"⚠️ Error de red guardando {datos.get('nombre_proyecto')}: {e}")
            return "error"

    def guardar_proyectos(self, lista: list[dict]) -> dict:
        """Guarda una lista de proyectos y devuelve estadísticas."""
        guardados = 0
        duplicados = 0
        errores = 0

        for datos in lista:
            resultado = self.guardar_proyecto(datos)
            if resultado == "guardado":
                guardados += 1
            elif resultado == "duplicado":
                duplicados += 1
            else:
                errores += 1

        return {"guardados": guardados, "duplicados": duplicados, "errores": errores}
