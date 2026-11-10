# src/tools/PitchValidatorTool.py
import json
from typing import Dict, Tuple
from base.ToolInterface import ToolInterface
from schemas.midi_schemas import TrackSpec


class PitchValidatorTool(ToolInterface):
    """
    Herramienta para validar y corregir los rangos de altura (pitch) MIDI según el tipo de instrumento.
    Si una nota excede los límites, la transpone por octavas (+/-12 semitonos) para mantener la armonía.
    """

    # Límites estándar [min_pitch, max_pitch] en notas MIDI (0-127)
    DEFAULT_RANGES: Dict[str, Tuple[int, int]] = {
        "bass": (28, 52),       # E1 a E3 (Bajo)
        "chords": (48, 76),     # C3 a E5 (Teclados / Acompañamiento)
        "piano": (48, 84),      # C3 a C6
        "lead": (60, 96),       # C4 a C7 (Melodía / Solos)
        "melody": (60, 96),     # C4 a C7
        "drums": (35, 81),      # Mapa estándar de percusión GM (Canal 10)
    }

    def _determine_range(self, track: TrackSpec) -> Tuple[int, int]:
        """Determina el rango de notas permitido analizando las propiedades de la pista."""
        if track.is_percussion:
            return self.DEFAULT_RANGES["drums"]

        name_lower = track.name.lower()
        for key, rng in self.DEFAULT_RANGES.items():
            if key in name_lower:
                return rng

        # Mapeo por número de Programa General MIDI si el nombre no coincide
        if 32 <= track.program <= 39:   # Synth/Electric Bass
            return self.DEFAULT_RANGES["bass"]
        elif 80 <= track.program <= 95:  # Synth Leads
            return self.DEFAULT_RANGES["lead"]

        # Rango por defecto amplio para instrumentos no clasificados
        return (36, 96)

    def execute(self, argumento: str) -> str:
        try:
            # 1. Limpieza de posible formato markdown
            argumento_limpio = argumento.replace('```json', '').replace('```', '').strip()
            data = json.loads(argumento_limpio)

            # 2. Deserialización y determinación de límites
            if "notes" in data:
                track = TrackSpec.model_validate(data)
                min_pitch, max_pitch = self._determine_range(track)
            elif "track" in data:
                track = TrackSpec.model_validate(data["track"])
                default_min, default_max = self._determine_range(track)
                min_pitch = data.get("min_pitch", default_min)
                max_pitch = data.get("max_pitch", default_max)
            else:
                return "Error: Formato de entrada no válido. Se esperaba un JSON de TrackSpec."

            notas_corregidas = 0

            # 3. Ajuste de notas por octavas
            for note in track.notes:
                # La percusión no se transpone por octavas ya que cada nota es un parche/platillo diferente
                if track.is_percussion:
                    continue

                pitch_original = note.pitch

                # Corrección octavada
                while note.pitch < min_pitch:
                    note.pitch += 12
                while note.pitch > max_pitch:
                    note.pitch -= 12

                # Recorte de seguridad si sigue fuera de rango por valores extremos del LLM
                note.pitch = min(max(note.pitch, min_pitch), max_pitch)

                if note.pitch != pitch_original:
                    notas_corregidas += 1

            # 4. Respuesta con la pista corregida y métricas de ajuste
            resultado = {
                "status": "success",
                "notas_ajustadas": notas_corregidas,
                "rango_aplicado": {"min": min_pitch, "max": max_pitch},
                "track": track.model_dump()
            }
            return json.dumps(resultado, ensure_ascii=False)

        except Exception as e:
            return f"Error en PitchValidatorTool: {type(e).__name__}: {str(e)}"