import requests
import re
from typing import Callable, Dict, Any


class BaseAgent:
    def __init__(self, nombre: str, modelo: str, system_prompt: str, herramientas: Dict[str, Callable]):
        self.nombre = nombre
        self.modelo = modelo
        self.system_prompt = system_prompt
        self.herramientas = herramientas  # Diccionario { 'nombre_herramienta': funcion_python }

    def llamar_llm(self, prompt_completo: str) -> str:
        """Comunica con el modelo local de Ollama de forma encapsulada."""
        url = "http://10.111.13.28:11434/api/generate"
        payload = {
            "model": self.modelo,
            "prompt": prompt_completo,
            "stream": False,
            "options": {
                "stop": ["Observación:", "Observacion:", "Observación:\n"]
            }
        }
        try:
            respuesta = requests.post(url, json=payload, timeout=120)
            respuesta.raise_for_status()
            return respuesta.json().get("response", "")
        except Exception as e:
            return f"Error conectando con Ollama: {str(e)}"

    def ejecutar(self, consulta: str, max_iter: int = 5) -> str:
        """El motor de la máquina de estados ReAct."""
        historial = f"{self.system_prompt}\nPregunta: {consulta}\nPensamiento: "

        print(f"\n[{self.nombre}] Iniciando análisis...")

        for i in range(max_iter):
            texto_generado = self.llamar_llm(historial)

            # Truncamiento defensivo
            if "Observación:" in texto_generado:
                texto_generado = texto_generado.split("Observación:")[0]

            historial += texto_generado

            # Condición de salida
            if "Respuesta Final:" in texto_generado:
                respuesta = texto_generado.split("Respuesta Final:")[-1].strip()
                print(f"[{self.nombre}] Tarea completada.")
                return respuesta

            # Parseo de la Acción
            patron = r"Acción:\s*(.*?)\nEntrada de la Acción:\s*(.*)"
            match = re.search(patron, texto_generado)

            if match:
                nombre_herramienta = match.group(1).strip()
                argumento = match.group(2).strip()

                print(f"  └─ [{self.nombre}] Usa herramienta: {nombre_herramienta}")

                # Ejecución dinámica desde el diccionario de herramientas
                funcion_actuador = self.herramientas.get(nombre_herramienta)

                if funcion_actuador:
                    resultado_real = funcion_actuador(argumento)
                else:
                    resultado_real = f"Error: La herramienta {nombre_herramienta} no está en mi caja de herramientas."

                historial += f"\nObservación: {resultado_real}\nPensamiento: "
            else:
                historial += "\nObservación: Error de formato. Usa 'Acción:' y 'Entrada de la Acción:'.\nPensamiento: "

        return f"[{self.nombre}] Fallo: Límite de iteraciones alcanzado."