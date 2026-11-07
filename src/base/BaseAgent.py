# src/base/BaseAgent.py
import re
from typing import Dict, List
from base.LLMClient import LLMClient
from base.ToolInterface import ToolInterface

class BaseAgent:
    def __init__(self, nombre: str, modelo: str, system_prompt: str, herramientas: Dict[str, ToolInterface], llm_client: LLMClient, stop_words: List[str] = None):
        self.nombre = nombre
        self.modelo = modelo
        self.system_prompt = system_prompt
        self.herramientas = herramientas
        self.llm_client = llm_client
        self.stop_words = stop_words or []

    def llamar_llm(self, prompt_completo: str) -> str:
        options = {
            "stop": self.stop_words,
            "temperature": 0.1 # Temperatura baja para que el modelo sea determinista y respete la sintaxis de las tools
        }
        return self.llm_client.generate(self.modelo, prompt_completo, options)

    def ejecutar(self, consulta: str) -> str:
        # 1. Armamos el contexto inicial con el prompt del sistema y la consulta
        prompt_actual = f"{self.system_prompt}\n\nConsulta del operador: {consulta}\n"
        
        # 2. Bucle de razonamiento (ReAct loop) - máximo 5 iteraciones para evitar bucles infinitos
        for paso in range(5):
            respuesta_parcial = self.llamar_llm(prompt_actual)
            
            # 3. Detectar si el LLM estructuró una llamada a herramienta
            # Busca "Acción: <nombre>" y "Entrada: <argumento>"
            match_accion = re.search(r'Acci[oó]n:\s*([a-zA-Z0-9_]+)', respuesta_parcial, re.IGNORECASE)
            # Como usamos stop_words, todo lo que sigue a 'Entrada:' es el argumento de la herramienta
            match_entrada = re.search(r'Entrada:\s*(.*)', respuesta_parcial, re.DOTALL | re.IGNORECASE)
            
            if match_accion and match_entrada:
                nombre_herramienta = match_accion.group(1).strip()
                argumento = match_entrada.group(1).strip()
                
                # Añadimos el razonamiento del modelo al historial de la conversación en memoria
                prompt_actual += f"{respuesta_parcial}\n"
                print(f"[Agente {self.nombre}] -> {respuesta_parcial}")
                print(f"  [Agente {self.nombre}] -> Solicitó usar herramienta: {nombre_herramienta}")
                
                if nombre_herramienta in self.herramientas:
                    try:
                        # 4. Ejecutamos el script de Pandas
                        resultado = self.herramientas[nombre_herramienta].execute(argumento)
                        # 5. Inyectamos la Observación de vuelta al prompt y el bucle vuelve a girar
                        prompt_actual += f"Observaci\u00f3n: {resultado}\n"
                        print(f"  [Sistema] -> Herramienta ejecutada con éxito. Devolviendo resultado al agente...")
                    except Exception as e:
                        prompt_actual += f"Observaci\u00f3n: Error al ejecutar {nombre_herramienta}: {str(e)}\n"
                        print(f"  [Sistema] -> Error en herramienta: {str(e)}")
                else:
                    prompt_actual += f"Observaci\u00f3n: La herramienta '{nombre_herramienta}' no existe.\n"
            else:
                # Si el modelo no pide una Acción, se considera que llegó a la conclusión final
                return respuesta_parcial
                
        return "Error: El agente superó el límite de razonamiento (5 pasos) sin llegar a una respuesta definitiva."