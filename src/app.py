# src/app.py
from pathlib import Path
from src.base.BaseAgent import BaseAgent
from base.config_loader import load_config
from base.ToolInterface import ToolInterface
from base.LLMClient import LLMClient
from utils.sanitization import sanitize_input
from tools.FiltrarDatosVivaldi import FiltrarDatosVivaldi
from tools.EjecutarCodigoPandas import EjecutarCodigoPandas
from tools.GenerarGrafico import GenerarGrafico

def load_tools(config):
    tools = {}
    for tool_name, tool_config in config['tools'].items():
        # Cargamos usando CamelCase para coincidir con la clase
        tool_class_name = tool_config['function'].split('.')[-1]
        tool_class = globals()[tool_class_name]
        tools[tool_name] = tool_class()
    return tools

def create_agents(config, tools):
    agents = {}
    llm_client = LLMClient("http://localhost:11434/api/generate")
    for agent_config in config['agents']:
        agent_tools = {name: tools[name] for name in agent_config['tools']}
        agent = BaseAgent(
            nombre=agent_config['name'],
            modelo=agent_config['model'],
            system_prompt=agent_config['system_prompt'],
            herramientas=agent_tools,
            llm_client=llm_client,
            stop_words=agent_config.get('stop_words', [])
        )
        agents[agent_config['name']] = agent
    return agents

def classify_intent(consulta: str) -> str:
    # Implementación de clasificación de intención (mock)
    return "DATOS"

if __name__ == "__main__":


    # 1. Obtenemos el directorio donde está app.py (la carpeta src)
    current_dir = Path(__file__).resolve().parent

    # 2. Construimos la ruta absoluta hacia config.json
    config_path = current_dir / 'config' / 'config.json'

    # 3. Cargamos la configuración pasando la ruta como string
    config = load_config(str(config_path))

    tools = load_tools(config)
    agents = create_agents(config, tools)

    while True:
        str_consulta = input("\nIngrese la consulta (ej. ¿Cuántos pozos están incrementando presión?):  ")

        # Interceptamos comandos de sistema antes de sanitizar o llamar al LLM
        comando = str_consulta.strip().lower()
        if comando in ['/reset', 'resetea', 'limpiar', 'clear', 'olvida', 'olvidate', ]:
            for agente in agents.values():
                agente.limpiar_memoria()
            print("\n==================================")
            print("🧠 MEMORIA DE CORTO PLAZO RESETEADA")
            print("==================================")
            continue  # Vuelve al inicio del bucle sin llamar al modelo

        consulta = sanitize_input(str_consulta)

        print(f"\n[Supervisor] Analizando consulta: '{consulta}'")
        ruta = classify_intent(consulta)
        print(f"[Supervisor] Decisión de enrutamiento: {ruta}")

        if ruta == "CALIDAD":
            respuesta_operador = agents['Inspector_DQ'].ejecutar(consulta)
        else:
            respuesta_operador = agents['Analista_Telemetria'].ejecutar(consulta)

        print("\n==================================")
        print("RESPUESTA AL OPERADOR:")
        print("==================================")
        print(respuesta_operador)