# src/base/BaseAgent.py
import re
from typing import Dict, List
from base.LLMClient import LLMClient
from base.ToolInterface import ToolInterface


class BaseAgent:
    def __init__(self, nombre: str, modelo: str, system_prompt: str, herramientas: Dict[str, ToolInterface],
                 llm_client: LLMClient, stop_words: List[str] = None):
        self.nombre = nombre
        self.modelo = modelo
        self.system_prompt = system_prompt
        self.herramientas = herramientas
        self.llm_client = llm_client
        self.stop_words = stop_words or []

        # NUEVO: Memoria persistente del agente
        self.historial_conversacion = []

    def limpiar_memoria(self):
        """Borra historial de conversacion a corto plazo del agente."""
        self.historial_conversacion = []

    def llamar_llm(self, prompt_completo: str) -> str:
        options = {
            "stop": self.stop_words,
            "temperature": 0.1
        }
        return self.llm_client.generate(self.modelo, prompt_completo, options)

    def ejecutar(self, consulta: str) -> str:
        # 1. Armamos el contexto base con el prompt del sistema
        prompt_base = f"{self.system_prompt}\n\n"

        # 2. Inyectamos la memoria de turnos anteriores si existe
        if self.historial_conversacion:
            prompt_base += "--- HISTORIAL DE CONVERSACIÓN PREVIA ---\n"
            for turno_usr, turno_agt in self.historial_conversacion:
                prompt_base += f"Operador: {turno_usr}\nTú: {turno_agt}\n\n"
            prompt_base += "----------------------------------------\n\n"

        # 3. Iniciamos el 'scratchpad' (bloc de notas) para el razonamiento actual
        prompt_actual = prompt_base + f"CONSULTA ACTUAL DEL OPERADOR: {consulta}\n"

        # MODIFICACIÓN 1: Aumentamos a 6 el límite para darle margen de depuración
        for paso in range(6):
            respuesta_parcial = self.llamar_llm(prompt_actual)

            print(f"[Agente {self.nombre}] -> {respuesta_parcial}")

            match_accion = re.search(r'Acci[oó]n:\s*([a-zA-Z0-9_]+)', respuesta_parcial, re.IGNORECASE)
            match_entrada = re.search(r'Entrada:\s*(.*)', respuesta_parcial, re.DOTALL | re.IGNORECASE)

            if match_accion and match_entrada:
                nombre_herramienta = match_accion.group(1).strip()
                argumento = match_entrada.group(1).strip()

                prompt_actual += f"{respuesta_parcial}\n"
                print(f"  [Agente {self.nombre}] -> Solicitó usar herramienta: {nombre_herramienta}")

                if nombre_herramienta in self.herramientas:
                    try:
                        resultado = self.herramientas[nombre_herramienta].execute(argumento)
                        prompt_actual += f"Observaci\u00f3n: {resultado}\n"

                        # MODIFICACIÓN 2: Imprimimos un extracto de lo que ve el LLM en lugar del mensaje estático
                        res_corto = str(resultado)[:150].replace('\n', ' ') + (
                            '...' if len(str(resultado)) > 150 else '')
                        print(f"  [Sistema] -> Resultado: {res_corto}")

                    except Exception as e:
                        prompt_actual += f"Observaci\u00f3n: Error al ejecutar {nombre_herramienta}: {str(e)}\n"
                        print(f"  [Sistema] -> Error en herramienta: {str(e)}")
                else:
                    prompt_actual += f"Observaci\u00f3n: La herramienta '{nombre_herramienta}' no existe.\n"
            else:
                # 4. Guardamos en el historial solo la consulta y la respuesta final,
                # omitiendo los pasos internos de ReAct para no saturar la memoria
                self.historial_conversacion.append((consulta, respuesta_parcial))
                return respuesta_parcial

        # MODIFICACIÓN 3: Anexamos la última respuesta parcial para saber por qué se trabó
        return "Error: El agente superó el límite de razonamiento intentando resolver el problema.\nÚltimo intento: " + respuesta_parcial