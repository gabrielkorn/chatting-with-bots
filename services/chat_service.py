from db import get_db_connection
from services.ollama_client import chat as ollama_chat
from services.bot_service import find_best_bot

MAX_MESSAGES = 20

def get_conversations():
    db = get_db_connection()
    return db.execute("SELECT * FROM conversations ORDER BY created_at DESC").fetchall()

def create_conversation():
    db = get_db_connection()
    count = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    cursor = db.cursor()
    cursor.execute("INSERT INTO conversations (name) VALUES (?)", (f"Conversation {count + 1}",))
    db.commit()
    return cursor.lastrowid

def get_messages(conversation_id):
    db = get_db_connection()
    return db.execute(
        "SELECT sender, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,)
    ).fetchall()

def handle_chat(conversation_id, user_message):
    db = get_db_connection()

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

    bot_response = ollama_chat(messages, model=model)
    bot_content = bot_response["message"]["content"]
    bot_name = bot["name"] if bot else None

    db.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)",
               (conversation_id, "bot", bot_content))
    db.commit()

    db.execute("""
        DELETE FROM messages WHERE conversation_id = ? AND id NOT IN (
            SELECT id FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?
        )
    """, (conversation_id, conversation_id, MAX_MESSAGES))
    db.commit()

    return bot_name, bot_content
