import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def generate_response(model, prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        },
        timeout=30,
    )
    response.raise_for_status()

    return response.json()["response"]
