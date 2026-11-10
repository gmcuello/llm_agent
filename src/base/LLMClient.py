# src/base/LLMClient.py
import requests
from typing import Optional, Dict, Any


class LLMClient:
    def __init__(self, url: str = "http://localhost:11434/api/generate"):
        self.url = url
        self.json_schema: Optional[Dict[str, Any]] = None # <-- Añadimos esta variable

    def generate(self, model: str, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options or {"temperature": 0.2}
        }

        # Inyección del esquema JSON estricto para Ollama
        if self.json_schema:
            payload["format"] = self.json_schema

        try:
            respuesta = requests.post(self.url, json=payload, timeout=120)
            respuesta.raise_for_status()
            return respuesta.json().get("response", "")
        except Exception as e:
            return f"Error conectando con LLM: {str(e)}"