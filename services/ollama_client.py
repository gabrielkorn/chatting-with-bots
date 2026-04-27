import os
import requests
from flask import current_app

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434") #"http://localhost:11434/v1/ollama"

# Function to send a messages to the Ollama API and get a response
def chat(messages, model="qwen:0.5b"):
    try:
        payload = {"model": model,
                   "messages": messages,
                   "stream": False
                }
        response = requests.post(f"{OLLAMA_API_URL}/api/chat", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        current_app.logger.error(f"Error communicating with Ollama API: {e}")
        return {"error": "Failed to communicate with Ollama API"}
    
# Function to get available models from Ollama API
def get_models():
    try:
        response = requests.get(f"{OLLAMA_API_URL}/api/tags")
        models = response.json().get("models", [])
        return models
    except requests.RequestException as e:
        current_app.logger.error(f"Error fetching models from Ollama API: {e}")
        return {"error": "Failed to fetch models from Ollama API"}