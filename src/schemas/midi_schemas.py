# src/schemas/midi_schemas.py
from typing import List
from pydantic import BaseModel, Field

# --- CAPA FÍSICA MIDI ---
class MidiNote(BaseModel):
    pitch: int = Field(..., ge=0, le=127)
    start_beat: float = Field(..., ge=0.0)
    duration_beats: float = Field(..., gt=0.0)
    velocity: int = Field(default=100, ge=1, le=127)

class TrackSpec(BaseModel):
    name: str
    program: int = Field(default=0, ge=0, le=127)
    is_percussion: bool = Field(default=False)
    notes: List[MidiNote]

# --- CAPA SEMÁNTICA (EL LENGUAJE DE LOS AGENTES) ---
class BarSpec(BaseModel):
    bar_number: int
    harmony_line: str = Field(..., description="Acordes y su figura rítmica. Ej: '[I] (blanca), [ii] (negra)'")
    melody_line: str = Field(..., description="Notas exactas y figuras. Ej: 'C5 (negra), silencio (corchea)'")

class LeadSheet(BaseModel):
    title: str
    bpm: int = Field(default=120, ge=40, le=240)
    key: str = Field(..., description="Tonalidad base. Ej: 'Do Mayor'")
    time_signature: str = Field(default="4/4")
    total_bars: int
    bars: List[BarSpec]

class SemanticTrack(BaseModel):
    razonamiento: str = Field(..., description="Piensa paso a paso.")
    name: str
    program: int = Field(default=0)
    bars: List[str] = Field(..., description="Arreglo de strings. Cada string corresponde a un compás del LeadSheet.")

class CompositionSpec(BaseModel):
    title: str
    bpm: int
    key: str
    total_bars: int
    tracks: List[TrackSpec]