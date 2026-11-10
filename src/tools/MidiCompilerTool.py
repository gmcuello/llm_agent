# src/tools/MidiCompilerTool.py
import json
import pretty_midi
from pathlib import Path
from base.ToolInterface import ToolInterface
from schemas.midi_schemas import CompositionSpec


class MidiCompilerTool(ToolInterface):
    """
    Herramienta para compilar un esquema CompositionSpec (JSON) a un archivo binario MIDI (.mid).
    """

    def __init__(self):
        # Aseguramos que la ruta 'outputs' se cree en la misma carpeta donde reside src/app.py
        current_dir = Path(__file__).resolve().parent.parent
        self.output_dir = current_dir / "outputs"

        # mkdir(parents=True) asegura que si faltan carpetas intermedias, también las cree
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, argumento: str) -> str:
        try:
            # Parsear entrada JSON
            data = json.loads(argumento)
            spec = CompositionSpec.model_validate(data)

            midi_data = pretty_midi.PrettyMIDI(initial_tempo=spec.bpm)
            seconds_per_beat = 60.0 / spec.bpm

            for track_spec in spec.tracks:
                instrument = pretty_midi.Instrument(
                    program=track_spec.program,
                    is_drum=track_spec.is_percussion,
                    name=track_spec.name
                )

                for note_info in track_spec.notes:
                    start_time = note_info.start_beat * seconds_per_beat
                    end_time = (note_info.start_beat + note_info.duration_beats) * seconds_per_beat

                    note = pretty_midi.Note(
                        velocity=min(max(int(note_info.velocity), 1), 127),
                        pitch=min(max(int(note_info.pitch), 0), 127),
                        start=start_time,
                        end=end_time
                    )
                    instrument.notes.append(note)

                midi_data.instruments.append(instrument)

            # Sanear el nombre del archivo para evitar errores de sistema operativo
            safe_title = spec.title.replace(' ', '_').replace('/', '-').replace('\\', '-').lower()
            output_file = self.output_dir / f"{safe_title}.mid"

            # Escribir a disco
            midi_data.write(str(output_file))

            # Verificar si el archivo realmente se escribió
            if output_file.exists():
                return f"Archivo MIDI generado exitosamente en: {output_file.resolve()}"
            else:
                return f"Error: La librería reportó éxito, pero el archivo no se encontró en el disco ({output_file.resolve()})."

        except Exception as e:
            return f"Error en la compilación MIDI: {type(e).__name__}: {str(e)}"