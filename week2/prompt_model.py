import os
import sys
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def estimate_tokens(text: str) -> int:
    """Fallback token estimator: 4 tokens per word."""
    return len(text.split()) * 4


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

_google_client = None

def _get_google_client() -> genai.Client:
    """Returns a cached Google Gemini client, creating one if needed."""
    global _google_client
    if _google_client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not found.")
        _google_client = genai.Client(api_key=api_key)
    return _google_client


GOOGLE_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview"
}

OLLAMA_MODELS = {
    "llama3.1",
    "phi3",
    "deepseek-r1:1.5b"
}


def prompt_google(model: str, prompt: str) -> tuple[str, int]:
    try:
        client = _get_google_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        tokens = 0
        if response.usage_metadata:
            tokens = (response.usage_metadata.prompt_token_count or 0) + \
                     (response.usage_metadata.candidates_token_count or 0)
        return response.text, tokens
    except Exception as e:
        return f"[Gemini Error] {str(e)}", 0


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
    elif model in GOOGLE_MODELS:
        return prompt_google(model, prompt)
    else:
        return f"[Error] Unsupported model: {model}", 0


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print('uv run prompt_model.py <model> "<prompt>"')
        return

    model = sys.argv[1]
    prompt = " ".join(sys.argv[2:])

    response = prompt_model(model, prompt)

    print("\n--- RESPONSE ---\n")
    print(response)


if __name__ == "__main__":
    main()