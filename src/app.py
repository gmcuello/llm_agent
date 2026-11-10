# src/app.py
import json
from pathlib import Path
from base.config_loader import load_config
from base.LLMClient import LLMClient
from base.BaseAgent import BaseAgent
from tools.MidiCompilerTool import MidiCompilerTool
from tools.QuantizerTool import QuantizerTool
from tools.PitchValidatorTool import PitchValidatorTool
from tools.MelodyParserTool import MelodyParserTool
from schemas.midi_schemas import CompositionSpec, TrackSpec
from utils.sanitization import sanitize_input, extract_json_from_response
from schemas.midi_schemas import TrackSpec, LeadSheet

def load_tools(config):
    tools_map = {
        "MidiCompilerTool": MidiCompilerTool(),
        "QuantizerTool": QuantizerTool(),
        "PitchValidatorTool": PitchValidatorTool(),
        "MelodyParserTool": MelodyParserTool()
    }
    return {name: tools_map[name] for name in config['tools']}


def create_agents(config, tools):
    agents = {}
    llm_client = LLMClient("http://localhost:11434/api/generate")

    # 1. Lee el modelo global configurado en el archivo
    default_model = config.get("default_model", "qwen2.5-coder:7b")

    for agent_config in config['agents']:
        agent_tools = {name: tools[name] for name in agent_config['tools'] if name in tools}

        # 2. Usa el modelo específico del agente si estuviera definido, o el global por defecto
        modelo_agente = agent_config.get('model', default_model)

        agent = BaseAgent(
            nombre=agent_config['name'],
            modelo=modelo_agente,
            system_prompt=agent_config['system_prompt'],
            herramientas=agent_tools,
            llm_client=llm_client,
            stop_words=agent_config.get('stop_words', [])
        )
        agents[agent_config['name']] = agent
    return agents


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    config_path = current_dir / 'config' / 'config.json'
    config = load_config(str(config_path))

    tools = load_tools(config)
    agents = create_agents(config, tools)

    while True:
        str_consulta = input("\nIngrese la descripción del tema MIDI (o 'salir'): ")
        if str_consulta.strip().lower() in ['salir', 'exit', 'quit']:
            break

        if str_consulta.strip().lower() in ['/reset', 'limpiar', 'clear']:
            for agente in agents.values():
                agente.limpiar_memoria()
            print("\n==================================")
            print("🧠 MEMORIA DE AGENTES RESETEADA")
            print("==================================")
            continue

        consulta = sanitize_input(str_consulta)
        print(f"\n==================================================")
        print(f"🎼 INICIANDO PIPELINE MULTI-AGENTE MIDI: '{consulta}'")
        print(f"==================================================")

        # --- [ETAPA 1: DIRECCIÓN Y LEADSHEET] ---
        print("\n--- [ETAPA 1: DIRECCIÓN Y LEADSHEET] ---")
        from schemas.midi_schemas import LeadSheet, SemanticTrack, TrackSpec

        agents['Director_Orquesta'].llm_client.json_schema = LeadSheet.model_json_schema()
        raw_director = agents['Director_Orquesta'].ejecutar(f"Genera el LeadSheet para: '{consulta}'")

        try:
            leadsheet_dict = extract_json_from_response(raw_director)
            leadsheet_context = json.dumps(leadsheet_dict, ensure_ascii=False)
            print(f"-> LeadSheet Generado: {leadsheet_dict.get('total_bars')} compases en {leadsheet_dict.get('key')}")
        except ValueError as e:
            print(f"❌ Error al generar LeadSheet: {e}")
            continue

        # --- [ETAPA 2, 3 y 4: INFERENCIA SEMÁNTICA] ---
        prompt_especialista = f"Genera tu pista basándote ESTRICTAMENTE en este LeadSheet:\n{leadsheet_context}"
        semantic_schema = SemanticTrack.model_json_schema()
        parser_tool = tools["MelodyParserTool"]

        print("\n--- [ETAPA 2: GENERACIÓN ARMÓNICA (CHORDS)] ---")
        agents['Agente_Armonico'].llm_client.json_schema = semantic_schema
        raw_chords = agents['Agente_Armonico'].ejecutar(prompt_especialista)
        chords_semantic = extract_json_from_response(raw_chords)

        print("\n--- [ETAPA 3: GENERACIÓN MELÓDICA (LEAD)] ---")
        agents['Agente_Melodico'].llm_client.json_schema = semantic_schema
        raw_lead = agents['Agente_Melodico'].ejecutar(prompt_especialista)
        lead_semantic = extract_json_from_response(raw_lead)

        print("\n--- [ETAPA 4: GENERACIÓN DE BAJO] ---")
        agents['Agente_Bajo'].llm_client.json_schema = semantic_schema
        raw_bass = agents['Agente_Bajo'].ejecutar(prompt_especialista)
        bass_semantic = extract_json_from_response(raw_bass)

        # --- [ETAPA 4.5: COMPILACIÓN MATEMÁTICA ANCLADA] ---
        # Asumimos que todos están en 4/4 (4 beats por compás)
        beats_per_bar = 4.0
        chords_midi, lead_midi, bass_midi = [], [], []

        for i in range(leadsheet_dict.get('total_bars', 1)):
            offset = i * beats_per_bar

            # Compilamos el compás I de cada instrumento pasándole el Offset exacto
            if i < len(chords_semantic.get('bars', [])):
                req = json.dumps({"start_offset": offset, "line": chords_semantic['bars'][i]})
                chords_midi.extend(json.loads(parser_tool.execute(req)))

            if i < len(lead_semantic.get('bars', [])):
                req = json.dumps({"start_offset": offset, "line": lead_semantic['bars'][i]})
                lead_midi.extend(json.loads(parser_tool.execute(req)))

            if i < len(bass_semantic.get('bars', [])):
                req = json.dumps({"start_offset": offset, "line": bass_semantic['bars'][i]})
                bass_midi.extend(json.loads(parser_tool.execute(req)))

        # --- [ETAPA 5: COMPILACIÓN BINARIA MIDI] ---
        print("\n--- [ETAPA 5: COMPILACIÓN BINARIA MIDI] ---")
        from schemas.midi_schemas import TrackSpec, CompositionSpec

        tracks_obj = [
            TrackSpec(name="Chords", program=0, notes=chords_midi),
            TrackSpec(name="Lead", program=80, notes=lead_midi),
            TrackSpec(name="Bass", program=33, notes=bass_midi)
        ]

        composition = CompositionSpec(
            title=leadsheet_dict.get("title", "Pieza_MultiAgente"),
            bpm=leadsheet_dict.get("bpm", 120),
            key=leadsheet_dict.get("key", "C major"),
            total_bars=leadsheet_dict.get("total_bars", 8),
            tracks=tracks_obj
        )

        compiler = tools["MidiCompilerTool"]
        resultado_compilacion = compiler.execute(composition.model_dump_json())
        print(
            f"\n==================================\nRESULTADO FINAL:\n==================================\n{resultado_compilacion}")