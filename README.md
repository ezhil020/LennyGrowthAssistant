# 🎙️ Lenny Growth Assistant

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-green.svg)
![React](https://img.shields.io/badge/React-18.0+-61dafb.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791.svg)

**Lenny Growth Assistant** is an agentic, RAG-powered chatbot designed to help Product Managers, Founders, and Growth Engineers extract actionable insights from the vast library of [Lenny's Podcast Transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts). 

It dynamically routes user intents to specialized conversational skills, queries a vector database for semantic context, and streams comprehensive growth strategies and artifact documents directly to the user.

---

## ✨ Key Features

- 🧠 **Agentic Intent Routing**: Analyzes conversation history and user queries to dynamically route requests to the correct specialized "Skill" (Q&A, Artifact Generation, or specific frameworks like Ship30).
- 🔍 **Hybrid Retrieval-Augmented Generation (RAG)**: Integrates `pgvector` for state-of-the-art semantic search across hundreds of podcast episodes.
- ⚡ **Local LLM Support**: Designed with privacy and cost-efficiency in mind, running natively on local models via **Ollama** (`qwen2.5:3b` and `nomic-embed-text`) with drop-in support for OpenAI.
- 🌊 **Real-Time SSE Streaming**: Lightning-fast token streaming provides an interactive, ChatGPT-like user experience.
- 📝 **Artifact Generation**: Automatically detects when a user needs a structured document (e.g., a PM framework, OKR template, or checklist) and generates a dedicated, persistent artifact alongside the chat.
- 🔄 **Smart Resumable Ingestion**: Asynchronous background workers pull, chunk, embed, and upsert transcript data directly from GitHub with intelligent resume capabilities.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with `pgvector` extension
- **ORM**: SQLAlchemy (Async)
- **LLM Engine**: Ollama (Local) / OpenAI API
- **Embeddings**: `nomic-embed-text` / `text-embedding-3-small`

### Frontend
- **Framework**: React 18 + Vite
- **State Management**: Zustand
- **Styling**: Vanilla CSS (Custom Design System)
- **Markdown Parsing**: `react-markdown` & `remark-gfm`

---

## 🚀 Getting Started

### 1. Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose
- [Ollama](https://ollama.com/) (if running local models)
- Python 3.11+ (for local development)
- Node.js 18+ (for local frontend development)

### 2. Environment Setup
Copy the example environment file and configure it:
```bash
cp .env.example .env
```
Ensure your `.env` is configured for your desired LLM provider (default is `ollama`).

### 3. Start the Database
The project requires a PostgreSQL instance with the `pgvector` extension. You can spin this up easily using Docker:
```bash
docker-compose up -d db
```

### 4. Install Dependencies
**Backend:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 5. Start the Services
Start the FastAPI Backend:
```bash
uvicorn backend.main:app --reload --port 8000
```
Start the React Frontend:
```bash
cd frontend
npm run dev
```

---

## 📚 Data Ingestion

Before the assistant can answer questions about Lenny's podcast, you must populate the vector database with the transcripts. 

Ensure Ollama is running and has the embedding model downloaded:
```bash
ollama pull nomic-embed-text
```

Trigger the asynchronous background ingestion process by making a POST request to the API:
```bash
curl -X POST http://localhost:8000/api/v1/ingest -H "Content-Type: application/json" -d '{"limit": 350}'
```
*Note: Depending on your hardware, embedding all ~300+ episodes locally via Ollama may take some time. The script is designed to safely resume if interrupted.*

---

## 🏗️ Architecture Overview

The system is built on a clean, scalable architectural pattern:

1. **API Layer (`/api/v1`)**: Exposes REST endpoints and SSE streams.
2. **Service Layer (`/services`)**: Orchestrates business logic, chat pipelines, and background tasks.
3. **Agentic Router (`/router`)**: Intercepts user queries and classifies the intent using an LLM to direct traffic.
4. **Skills (`/skills`)**: Isolated logic modules (e.g., `qa_skill`, `artifact_skill`) that execute specialized prompts and logic.
5. **Retrieval (`/retrieval`)**: Handles semantic chunking, vector embedding, and hybrid search against `pgvector`.
6. **Data Layer (`/repositories`)**: Async SQLAlchemy repositories handling all database transactions and ensuring safe rollbacks during failures.

---
