"""
services/bot_service.py
Manages bot vector embeddings and similarity-based bot selection for Robot Chat.
Created: 2026-04-26

Responsibilities:
- Generates and stores vector embeddings of bot system prompts via Ollama
- Finds the best matching bot for a user message using cosine similarity
- Prioritizes bots active in the current conversation over the global pool
"""

import os
import struct
import requests
from flask import current_app
from db import get_db_connection

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434")
EMBED_MODEL = "qwen:0.5b"

def _embed(text):
    """
    Sends text to Ollama's embedding endpoint and returns a float vector.
    Returns None if the request fails, which causes bot selection to be skipped.
    """
    try:
        response = requests.post(f"{OLLAMA_API_URL}/api/embed",
                                 json={"model": EMBED_MODEL, "input": text}, timeout=30)
        response.raise_for_status()
        return response.json()["embeddings"][0]
    except requests.RequestException as e:
        current_app.logger.error(f"Error embedding text: {e}")
        return None

def _pack(vector):
    """Packs a float vector into binary — required format for sqlite-vec storage and comparison."""
    return struct.pack(f"{len(vector)}f", *vector)

def store_bot_vector(bot_id):
    """
    Generates a vector embedding from a bot's system prompt and persists it to the database.
    Called when a bot is created so it is ready for similarity search immediately.
    """
    db = get_db_connection()
    bot = db.execute("SELECT system_prompt FROM bots WHERE id = ?", (bot_id,)).fetchone()
    if not bot or not bot["system_prompt"]:
        return
    vector = _embed(bot["system_prompt"])
    if vector:
        db.execute("UPDATE bots SET system_prompt_vector = ? WHERE id = ?",
                   (_pack(vector), bot_id))
        db.commit()

def embed_all_bots():
    """
    Backfills embeddings for any bots that do not have one yet.
    Runs at startup to handle bots added before the embedding logic existed.
    """
    db = get_db_connection()
    bots = db.execute(
        "SELECT id FROM bots WHERE system_prompt IS NOT NULL AND system_prompt_vector IS NULL"
    ).fetchall()
    for bot in bots:
        store_bot_vector(bot["id"])

def find_best_bot(user_message, conversation_id=None):
    """
    Returns the bot whose system prompt is most semantically similar to the user's message.
    Prefers bots assigned to the current conversation; falls back to all bots if none match.
    """
    vector = _embed(user_message)
    if not vector:
        return None
    db = get_db_connection()
    packed = _pack(vector)

    if conversation_id:
        result = db.execute("""
            SELECT bots.*, vec_distance_cosine(system_prompt_vector, ?) as distance
            FROM bots
            INNER JOIN conversation_bots ON bots.id = conversation_bots.bot_id
            WHERE bots.system_prompt_vector IS NOT NULL
              AND conversation_bots.conversation_id = ?
            ORDER BY distance ASC
            LIMIT 1
        """, (packed, conversation_id)).fetchone()
        if result:
            return result

    return db.execute("""
        SELECT *, vec_distance_cosine(system_prompt_vector, ?) as distance
        FROM bots
        WHERE system_prompt_vector IS NOT NULL
        ORDER BY distance ASC
        LIMIT 1
    """, (packed,)).fetchone()
