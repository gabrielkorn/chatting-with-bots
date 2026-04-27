"""
services/chat_service.py
Handles conversation and messaging logic for Robot Chat.
Created: 2026-04-26

Responsibilities:
- Creates and retrieves conversations and messages
- Routes each user message to the most relevant bot via vector similarity
- Maintains a rolling message history window to stay within model context limits
"""

from db import get_db_connection
from services.ollama_client import chat as ollama_chat
from services.bot_service import find_best_bot

# Maximum number of messages retained per conversation to keep model context manageable
MAX_MESSAGES = 20

def get_conversations():
    """Returns all conversations ordered by most recently created."""
    db = get_db_connection()
    return db.execute("SELECT * FROM conversations ORDER BY created_at DESC").fetchall()

def create_conversation():
    """
    Creates a new conversation with an auto-generated name and returns its ID.
    Name is based on total conversation count (e.g. 'Conversation 3').
    """
    db = get_db_connection()
    count = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    cursor = db.cursor()
    cursor.execute("INSERT INTO conversations (name) VALUES (?)", (f"Conversation {count + 1}",))
    db.commit()
    return cursor.lastrowid

def get_messages(conversation_id):
    """Returns all messages for a conversation in chronological order."""
    db = get_db_connection()
    return db.execute(
        "SELECT sender, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,)
    ).fetchall()

def handle_chat(conversation_id, user_message):
    """
    Processes a user message and returns a bot reply.

    - Selects the best matching bot using vector similarity on the user's message
    - Builds the message history in the format Ollama expects (system, assistant, user roles)
    - Saves both the user message and bot reply to the database
    - Trims the conversation to MAX_MESSAGES to prevent unbounded growth
    - Returns a tuple of (bot_name, reply_content)
    """
    db = get_db_connection()

    # Fetch recent history in descending order, then reverse to get chronological order for the model
    history = db.execute(
        "SELECT sender, content FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
        (conversation_id, MAX_MESSAGES)
    ).fetchall()

    bot = find_best_bot(user_message, conversation_id=conversation_id)
    model = bot["model"] if bot else "qwen:0.5b"

    messages = []
    if bot and bot["system_prompt"]:
        messages.append({"role": "system", "content": bot["system_prompt"]})

    messages += [
        {"role": "user" if m["sender"] == "user" else "assistant", "content": m["content"]}
        for m in reversed(history)
    ]
    messages.append({"role": "user", "content": user_message})

    db.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)",
               (conversation_id, "user", user_message))
    db.commit()

    bot_name = bot["name"] if bot else None
    bot_response = ollama_chat(messages, model=model)
    if "error" in bot_response:
        return bot_name, f"[Error: {bot_response['error']}]"
    bot_content = bot_response["message"]["content"]

    db.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)",
               (conversation_id, "bot", bot_content))
    db.commit()

    # Keep only the most recent MAX_MESSAGES per conversation
    db.execute("""
        DELETE FROM messages WHERE conversation_id = ? AND id NOT IN (
            SELECT id FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?
        )
    """, (conversation_id, conversation_id, MAX_MESSAGES))
    db.commit()

    return bot_name, bot_content
