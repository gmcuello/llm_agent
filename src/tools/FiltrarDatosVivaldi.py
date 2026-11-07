# src/tools/FiltrarDatosVivaldi.py
import json
import pandas as pd
from pathlib import Path
from base.ToolInterface import ToolInterface


class FiltrarDatosVivaldi(ToolInterface):
    """
    Herramienta para filtrar datos específicos de Vivaldi.
    Espera un argumento en formato JSON.
    Ejemplo de entrada: {"riesgo_pozo": "Alto"} o {"status": "Activo"}
    """

    def __init__(self):
        # Mantenemos la misma lógica de resolución dinámica de rutas que en EjecutarCodigoPandas
        current_dir = Path(__file__).resolve().parent
        rutas_posibles = [
            current_dir.parent.parent / 'diagnosticos_mock.pkl',
            current_dir.parent / 'diagnosticos_mock.pkl',
            current_dir.parent.parent / 'data' / 'diagnosticos_mock.pkl'
        ]
        self.pkl_path = next((ruta for ruta in rutas_posibles if ruta.exists()), rutas_posibles[0])
        self.df_cache = None

    def _load_dataframe(self) -> pd.DataFrame:
        if self.df_cache is None:
            if self.pkl_path.exists():
                self.df_cache = pd.read_pickle(self.pkl_path)
            else:
                raise FileNotFoundError(f"No se encontró el archivo de datos en: {self.pkl_path}")
        return self.df_cache.copy()

    def execute(self, argumento: str) -> str:
        try:
            # 1. El LLM debe enviar las condiciones como un diccionario JSON
            # Limpiamos posibles formatos de código markdown accidentales
            argumento_limpio = argumento.replace('```json', '').replace('```', '').strip()

            try:
                filtros = json.loads(argumento_limpio)
                if not isinstance(filtros, dict):
                    return "Error: El argumento debe ser un diccionario JSON (ej. {\"columna\": \"valor\"})."
            except json.JSONDecodeError:
                return f"Error de sintaxis: El LLM no envió un JSON válido. Recibido: {argumento}"

            # 2. Cargar datos
            df = self._load_dataframe()

            # 3. Aplicar los filtros iterativamente
            for columna, valor in filtros.items():
                if columna in df.columns:
                    df = df[df[columna] == valor]
                else:
                    return f"Error: La columna '{columna}' no existe en el dataset de Vivaldi. Columnas válidas: {list(df.columns)}"

            # 4. Formatear la respuesta para el agente
            if df.empty:
                return "El filtro se aplicó correctamente, pero no se encontraron registros que coincidan con la búsqueda."

            # Devolvemos un resumen para no desbordar la ventana de contexto del LLM
            resumen = f"Se encontraron {len(df)} registros. Muestra de los primeros 5 resultados:\n"
            resumen += df.head(5).to_string()
            return resumen

        except FileNotFoundError as fnf_err:
            return str(fnf_err)
        except Exception as e:
            return f"Error inesperado al ejecutar FiltrarDatosVivaldi: {type(e).__name__}: {str(e)}"