# src/base/config_loader.py
import json

def load_config(file_path):
    # Agregamos encoding='utf-8' para soportar tildes en los prompts
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)