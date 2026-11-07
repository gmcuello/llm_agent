# src/base/LLMClient.py
import requests

class LLMClient:
    def __init__(self, url: str):
        self.url = url

    def generate(self, model: str, prompt: str, options: dict) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }
        try:
            respuesta = requests.post(self.url, json=payload, timeout=120)
            respuesta.raise_for_status()
            return respuesta.json().get("response", "")
        except Exception as e:
            return f"Error conectando con LLM: {str(e)}"
