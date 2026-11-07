# src/utils/sanitization.py
import re

def sanitize_input(input_data: str) -> str:
    # Permite caracteres alfanuméricos, espacios y signos de puntuación clave
    # El guion (-) debe ir al final de la clase de caracteres para ser literal
    return re.sub(r'[^\w\s\?¿!¡.,;:()\[\]{}=\'"+*/<>-]', '', input_data)