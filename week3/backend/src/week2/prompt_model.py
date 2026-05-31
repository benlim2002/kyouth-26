import os
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def estimate_tokens(text: str) -> int:
    return len(text.split()) * 4


MODEL = os.getenv("MODEL")
DB_PATH = os.getenv("DB_PATH")
OLLAMA_URL = os.getenv("OLLAMA_URL")


OLLAMA_MODELS = {
    "llama3.1",
    "phi3",
    "deepseek-r1:1.5b"
}

def prompt_ollama(model: str, prompt: str) -> tuple[str, int]:
    try:
        payload = {"model": model, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code != 200:
            return f"[Ollama Error] {response.status_code} {response.text}", 0
        data = response.json()
        text = data.get("response", "No response returned.")
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        if tokens == 0:
            tokens = estimate_tokens(prompt) + estimate_tokens(text)
        return text, tokens
    except requests.exceptions.RequestException as e:
        return f"[Ollama Connection Error] {str(e)}", 0
    except Exception as e:
        return f"[Unexpected Ollama Error] {str(e)}", 0

def prompt_model(model: str, prompt: str) -> tuple[str, int]:
    if model in OLLAMA_MODELS:
        return prompt_ollama(model, prompt)
    else:
        return f"[Error] Unsupported model: {model}", 0