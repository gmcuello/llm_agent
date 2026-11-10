# src/tools/QuantizerTool.py
import json
from base.ToolInterface import ToolInterface


class QuantizerTool(ToolInterface):
    """
    Ajusta los start_beats de una lista de notas al valor de rejilla más cercano (grid step).
    """

    def execute(self, argumento: str) -> str:
        try:
            data = json.loads(argumento)
            grid = float(data.get("grid", 0.25))  # Por defecto corchea/semicorchea
            notes = data.get("notes", [])

            for note in notes:
                raw_start = note["start_beat"]
                note["start_beat"] = round(raw_start / grid) * grid

            return json.dumps(notes)
        except Exception as e:
            return f"Error en la cuantización: {str(e)}"