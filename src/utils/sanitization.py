# src/utils/sanitization.py
import re
import json
from typing import Dict, Any


def sanitize_input(input_data: str) -> str:
    return re.sub(r'[^\w\s\?¿!¡.,;:()\[\]{}=\'"+*/<>-]', '', input_data)


def extract_json_from_response(text: str) -> Dict[str, Any]:
    """
    Extrae y parsea el objeto JSON del texto, limpiando previamente
    posibles comentarios de código introducidos por el LLM.
    """
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if not json_match:
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)

    if json_match:
        raw_json = json_match.group(1)

        # Limpieza de comentarios que rompen el parser de Python
        raw_json = re.sub(r'//.*', '', raw_json)  # Comentarios de una línea
        raw_json = re.sub(r'/\*.*?\*/', '', raw_json, flags=re.DOTALL)  # Multilínea

        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parseando JSON tras limpiarlo: {str(e)}\n\nJSON resultante:\n{raw_json}")

    raise ValueError(f"No se encontró un JSON válido. Texto original:\n{text}")