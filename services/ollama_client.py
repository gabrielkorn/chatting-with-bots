"""
services/ollama_client.py
HTTP client for communicating with the Ollama API in Robot Chat.
Created: 2026-04-26

Responsibilities:
- Sends chat messages to a locally running Ollama model and returns the response
- Retrieves the list of available models pulled into Ollama
"""

import os
import requests
from flask import current_app

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434") 

def chat(messages, model="qwen:0.5b"):
    """
    Sends a list of messages to the Ollama chat API and returns the full response.
    Messages should contain 'role' and 'content' keys.
    Returns an error if the request fails.
    """
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

def get_models():
    """
    Fetches the list of models currently pulled and available in Ollama.
    Returns an error if the request fails.
    """
    try:
        response = requests.get(f"{OLLAMA_API_URL}/api/tags")
        models = response.json().get("models", [])
        return models
    except requests.RequestException as e:
        current_app.logger.error(f"Error fetching models from Ollama API: {e}")
        return {"error": "Failed to fetch models from Ollama API"}