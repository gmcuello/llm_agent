# src/tools/EjecutarCodigoPandas.py
import pandas as pd
import io
import sys
from pathlib import Path
from base.ToolInterface import ToolInterface

class EjecutarCodigoPandas(ToolInterface):
    """
    Herramienta que permite al agente ejecutar código de Pandas generado dinámicamente
    para realizar análisis exploratorio y filtrado sobre datos de telemetría.
    """
    
    def __init__(self):
        current_dir = Path(__file__).resolve().parent

        # Definimos las posibles ubicaciones donde podría estar tu .pkl
        rutas_posibles = [
            current_dir.parent.parent / 'diagnosticos_mock.pkl',  # En la raíz (llm_agent/)
            current_dir.parent / 'diagnosticos_mock.pkl',  # En la carpeta (src/)
            current_dir.parent.parent / 'data' / 'diagnosticos_mock.pkl'  # Si creas una carpeta de datos
        ]

        # Asignamos la primera ruta que físicamente exista
        self.pkl_path = next((ruta for ruta in rutas_posibles if ruta.exists()), rutas_posibles[0])
        self.df_cache = None


    def _load_dataframe(self) -> pd.DataFrame:
        if self.df_cache is None:
            if self.pkl_path.exists():
                self.df_cache = pd.read_pickle(self.pkl_path)
            else:
                raise FileNotFoundError(f"No se encontró el archivo de datos en: {self.pkl_path}")
        return self.df_cache.copy() # Retornamos una copia para evitar que el LLM mute el estado global
    
    def execute(self, argumento: str) -> str:
        # Redirigir la salida estándar para capturar los 'print()' que haga el LLM
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()

        try:
            # Cargar el DataFrame desde el pkl al momento de ejecutar la herramienta
            df = self._load_dataframe()
            
            # Entorno controlado donde el LLM tiene acceso a pandas y al dataframe 'df'
            local_env = {'pd': pd, 'df': df}
            
            # Limpiar posibles bloques de markdown en el string
            codigo = argumento.replace('```python', '').replace('```', '').strip()
            
            # Ejecutar el código generado por el agente
            exec(codigo, {}, local_env)
            
            # Recuperar la salida impresa
            output = redirected_output.getvalue().strip()
            
            # Si el agente no usó print(), pero dejó el resultado en una variable 'resultado'
            if not output and 'resultado' in local_env:
                output = str(local_env['resultado'])
            elif not output:
                output = "Ejecución exitosa, pero no se generó salida. Usa print() o guarda en la variable 'resultado'."
                
            return output
            
        except FileNotFoundError as fnf_err:
            return str(fnf_err)
        except Exception as e:
            return f"Error en la ejecución del código: {type(e).__name__}: {str(e)}"
            
        finally:
            # Restaurar la salida estándar al sistema original
            sys.stdout = old_stdout