# Chatting with Bots

A chatroom where multiple AI bots where multiple AI bots (LLMs) can participate, each with a distinct role. The app uses vector similarity to automatically route each message to the most relevant bot.

## Tech Stack

- **Backend**: Python / Flask
- **Frontend**: HTML + HTMX (no JS framework)
- **Database**: SQLite3 + [sqlite-vec] (https://github.com/asg017/sqlite-vec) for vector similarity
- **AI**: [Ollama](https://ollama.com) for running local LLMs
- **Containers**: Docker Compose

---

## Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/)
- Git

---

## Setup & Running

### 1. Clone the repo

```bash
git clone <repo-url>
cd chatting-with-bots
```

### 2. Create a `.env` file

The app requires a `.env` file to exist:

```bash
# Windows
type nul > .env

# Mac/Linux
touch .env
```

### 3. Start the containers

```bash
docker-compose up --build
```

This will:
- Pull the `ollama/ollama` image from Docker Hub
- Build the Flask app image
- Start both services

### 4. Pull a model into Ollama

In the terminal, pull the default model:

```bash
docker exec ollama-container ollama pull qwen:0.5b
```

Wait for the download to complete before sending messages. You can add more models later via the Bots page.

### 5. Open the app

Visit [http://localhost:5000](http://localhost:5000)

---

## Usage

1. **Create a bot** — go to **Manage Bots**, give it a name, system prompt, and select a model
2. **Start a conversation** — click **+ New Chat** in the sidebar
3. **Assign bots** — check bots in the right panel to activate them for the conversation
4. **Chat** — type a message and hit Send. The app routes your message to the most relevant active bot using vector similarity on the system prompts

---

## Stopping the App

Stop containers (data is preserved):
```bash
docker-compose stop
```

## Adding More Models

Any model available on [ollama.com/library](https://ollama.com/library) can be used:

```bash
docker exec ollama-container ollama pull llama3.2:1b
docker exec ollama-container ollama pull phi3:mini
```

Once pulled, models appear in the dropdown when creating or editing a bot.