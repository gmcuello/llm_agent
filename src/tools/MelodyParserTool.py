# src/tools/MelodyParserTool.py
import re
import json
from base.ToolInterface import ToolInterface


class MelodyParserTool(ToolInterface):
    FIGURES_TO_BEATS = {
        "redonda": 4.0, "whole": 4.0,
        "blanca": 2.0, "half": 2.0,
        "negra": 1.0, "quarter": 1.0,
        "corchea": 0.5, "eighth": 0.5,
        "semicorchea": 0.25, "sixteenth": 0.25,
        "blanca con puntillo": 3.0, "dotted-half": 3.0,
        "negra con puntillo": 1.5, "dotted-quarter": 1.5,
        "corchea con puntillo": 0.75, "dotted-eighth": 0.75
    }

    NOTE_TO_MIDI = {
        "C": 12, "DO": 12, "C#": 13, "DO#": 13, "DB": 13, "REB": 13,
        "D": 14, "RE": 14, "D#": 15, "RE#": 15, "EB": 15, "MIB": 15,
        "E": 16, "MI": 16, "F": 17, "FA": 17, "F#": 18, "FA#": 18,
        "GB": 18, "SOLB": 18, "G": 19, "SOL": 19, "G#": 20, "SOL#": 20,
        "AB": 20, "LAB": 20, "A": 21, "LA": 21, "A#": 22, "LA#": 22,
        "B": 23, "SI": 23
    }

    def _parse_pitch(self, note_str: str) -> int:
        match = re.match(r'([A-Za-z]+[#b]?)(-?\d)?', note_str)
        if not match: return -1
        note_name = match.group(1).upper()
        octave = int(match.group(2)) if match.group(2) else 4
        if note_name in self.NOTE_TO_MIDI:
            return self.NOTE_TO_MIDI[note_name] + (octave * 12)
        return -1

    def execute(self, argumento: str) -> str:
        # Ahora espera un JSON: {"start_offset": 4.0, "line": "C4 (negra)..."}
        try:
            data = json.loads(argumento)
            base_offset = float(data.get("start_offset", 0.0))
            line = data.get("line", "")
        except:
            # Fallback por si acaso
            base_offset = 0.0
            line = argumento

        tokens = [t.strip() for t in line.replace('```', '').replace('\n', ',').split(',')]
        current_beat = base_offset
        midi_notes = []

        for token in tokens:
            if not token: continue

            match_figura = re.search(r'\((.*?)\)', token)
            figura_str = match_figura.group(1).lower() if match_figura else "negra"
            duration = self.FIGURES_TO_BEATS.get(figura_str, 1.0)

            notas_str = re.sub(r'\(.*?\)', '', token).strip()
            if not notas_str:
                notas_str = "C4"

            if notas_str.lower() not in ["silencio", "rest"]:
                notas_individuales = re.split(r'[\+\s]+', notas_str)
                for n in notas_individuales:
                    if not n: continue
                    pitch_val = self._parse_pitch(n)
                    if pitch_val >= 0:
                        midi_notes.append({
                            "pitch": pitch_val,
                            "start_beat": round(current_beat, 3),
                            "duration_beats": duration,
                            "velocity": 100
                        })

            current_beat += duration

        return json.dumps(midi_notes, indent=2)