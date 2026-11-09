# src/tools/GenerarGrafico.py
import io
import sys
import uuid
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from base.ToolInterface import ToolInterface

class GenerarGrafico(ToolInterface):
    """
    Herramienta para generar gráficos con matplotlib y pandas.
    Ejecuta el código del LLM y guarda automáticamente la figura resultante en disco.
    """
    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent.parent
        
        # Búsqueda del pkl
        rutas_posibles = [
            base_dir / 'diagnosticos_mock.pkl',
            base_dir / 'src' / 'diagnosticos_mock.pkl',
            base_dir / 'data' / 'diagnosticos_mock.pkl'
        ]
        self.pkl_path = next((ruta for ruta in rutas_posibles if ruta.exists()), rutas_posibles[0])
        self.df_cache = None
        
        # Directorio para guardar los gráficos generados
        self.output_dir = base_dir / 'outputs'
        self.output_dir.mkdir(exist_ok=True)

    def _load_dataframe(self) -> pd.DataFrame:
        if self.df_cache is None:
            if self.pkl_path.exists():
                self.df_cache = pd.read_pickle(self.pkl_path)
            else:
                raise FileNotFoundError(f"No se encontró el archivo de datos en: {self.pkl_path}")
        return self.df_cache.copy()

    def execute(self, argumento: str) -> str:
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()
        try:
            df = self._load_dataframe()
            
            # Limpiar cualquier figura previa en memoria
            plt.clf()
            
            # Entorno con pandas y matplotlib inyectados
            local_env = {'pd': pd, 'df': df, 'plt': plt}
            
            codigo = argumento.replace('```python', '').replace('```', '').strip()
            exec(codigo, {}, local_env)
            
            # El "truco": verificar si el LLM dejó una figura activa en memoria
            if plt.get_fignums():
                filename = f"grafico_{uuid.uuid4().hex[:6]}.png"
                filepath = self.output_dir / filename
                plt.savefig(filepath, bbox_inches='tight')
                plt.close('all') # Liberar memoria
                return f"¡Éxito! El gráfico fue generado y guardado en la ruta: {filepath}"
            else:
                output = redirected_output.getvalue().strip()
                return f"El código se ejecutó, pero no se dibujó ningún gráfico. Salida: {output}"

        except Exception as e:
            return f"Error al generar el gráfico: {type(e).__name__}: {str(e)}"
        finally:
            sys.stdout = old_stdout