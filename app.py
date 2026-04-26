from flask import Flask, render_template, request, redirect, url_for
from flask_htmx import HTMX
from db import init_db, get_db_connection
from services.chat_service import create_conversation, handle_chat, get_conversations, get_messages
from services.bot_service import embed_all_bots, store_bot_vector
from services.ollama_client import get_models

app = Flask(__name__)
htmx = HTMX(app)
with app.app_context():
    init_db()
    embed_all_bots()

@app.route("/")
def index():
    conversations = get_conversations()
    all_bots = get_db_connection().execute("SELECT id, name FROM bots ORDER BY name").fetchall()
    return render_template("index.html", conversations=conversations, all_bots=all_bots)

@app.route("/conversations/new", methods=["POST"])
def new_conversation():
    conversation_id = create_conversation()
    return redirect(url_for("view_conversation", conversation_id=conversation_id))

@app.route("/convo/<int:conversation_id>")
def view_conversation(conversation_id):
    conversations = get_conversations()
    messages = get_messages(conversation_id)
    db = get_db_connection()
    all_bots = db.execute("SELECT id, name FROM bots ORDER BY name").fetchall()
    active_bot_ids = {row["bot_id"] for row in db.execute(
        "SELECT bot_id FROM conversation_bots WHERE conversation_id = ?", (conversation_id,)
    ).fetchall()}
    return render_template("index.html", conversations=conversations, messages=messages,
                           active_id=conversation_id, all_bots=all_bots, active_bot_ids=active_bot_ids)

@app.route("/convo/<int:conversation_id>/bots/<int:bot_id>/toggle", methods=["POST"])
def toggle_conversation_bot(conversation_id, bot_id):
    db = get_db_connection()
    existing = db.execute(
        "SELECT 1 FROM conversation_bots WHERE conversation_id = ? AND bot_id = ?",
        (conversation_id, bot_id)
    ).fetchone()
    if existing:
        db.execute("DELETE FROM conversation_bots WHERE conversation_id = ? AND bot_id = ?",
                   (conversation_id, bot_id))
    else:
        db.execute("INSERT INTO conversation_bots (conversation_id, bot_id) VALUES (?, ?)",
                   (conversation_id, bot_id))
    db.commit()
    return "", 204

@app.route("/message/send", methods=["POST"])
def post_message():
    message = request.form["message"]
    conversation_id = request.form["conversation_id"]
    bot_name, reply = handle_chat(conversation_id, message)
    return render_template("message.html", message=message, reply=reply, bot_name=bot_name)

@app.route("/bots")
def bots():
    all_bots = get_db_connection().execute("SELECT * FROM bots ORDER BY created_at DESC").fetchall()
    models = get_models()
    return render_template("bots.html", bots=all_bots, models=models)

@app.route("/bots", methods=["POST"])
def create_bot():
    db = get_db_connection()
    name = request.form["name"]
    system_prompt = request.form["system_prompt"]
    model = request.form["model"]
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO bots (name, system_prompt, model) VALUES (?, ?, ?)",
        (name, system_prompt, model)
    )
    db.commit()
    store_bot_vector(cursor.lastrowid)
    return redirect(url_for("bots"))

@app.route("/bots/<int:bot_id>/delete", methods=["POST"])
def delete_bot(bot_id):
    db = get_db_connection()
    db.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
    db.commit()
    return redirect(url_for("bots"))

@app.route("/bots/<int:bot_id>/model", methods=["POST"])
def update_bot_model(bot_id):
    db = get_db_connection()
    db.execute("UPDATE bots SET model = ? WHERE id = ?", (request.form["model"], bot_id))
    db.commit()
    return redirect(url_for("bots"))
