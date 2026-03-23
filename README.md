# 🌙 Dione — Sentient Local AI Assistant

> **"Intelligence that lives with you, not above you."**

Dione is a **Local Large Action Model (LAM) Orchestration Engine** — a privacy-first, agentic AI personal assistant that runs entirely on your hardware. Unlike cloud-dependent assistants, Dione keeps your data sovereign, builds a living knowledge graph of your digital life, and understands the emotional context of your world.

## ✨ Star Factors

### 1. 🧠 Personal Knowledge Graph
Not flat-file memory — a **structured graph database** connecting people, events, documents, and preferences with typed relationships. When you say "send that thing to Alice," Dione traverses the graph and *knows* what you mean.

### 2. 💜 Sentiment Intelligence Engine
Every incoming message is analyzed for emotional weight — urgency, frustration, importance, tone. Dione dynamically prioritizes, escalates, or batches information based on how it *feels*, not just what it says.

### 3. 📱 Mobile Chat Companion
Dione lives on your PC (local LLM + engine). You talk to it through a beautiful mobile app — proactive notifications, contextual suggestions, and a conversational UI that makes it feel like texting a brilliant friend.

### 4. 🔒 Zero-Trust Local Intelligence
All reasoning happens on YOUR device. No data leaves your machine except the specific API calls YOU authorize (sending an email, posting a message). Your digital life stays yours.

## 🏗️ Architecture

```
┌──────────────────────────────────────────┐
│           YOUR PC (Dione's Home)          │
│                                           │
│  ┌──────────┐  ┌───────────────────────┐ │
│  │ Local LLM │  │   Knowledge Graph     │ │
│  │ (Mistral/ │  │ (People, Events,     │ │
│  │  Llama)   │  │  Docs, Relations)    │ │
│  └─────┬─────┘  └──────────┬───────────┘ │
│        │                   │              │
│  ┌─────▼───────────────────▼───────────┐ │
│  │      Dione Orchestration Engine      │ │
│  │   ReAct Loop · Plugin System ·       │ │
│  │   Sentiment Engine · Memory Manager  │ │
│  └──────────────┬──────────────────────┘ │
│                 │  FastAPI (REST + WS)    │
└─────────────────┼────────────────────────┘
                  │
     ┌────────────┼──────────────┐
     │            │              │
 ┌───▼────┐  ┌───▼────┐  ┌─────▼──────┐
 │ Mobile  │  │ PC CLI │  │  Plugins   │
 │  App    │  │ / Web  │  │ (WhatsApp, │
 │(Flutter)│  │   UI   │  │ Gmail ...) │
 └────────┘  └────────┘  └────────────┘
```

## 📂 Project Structure

```
dione/
├── server/                    # Python backend (Dione's brain)
│   ├── core/                  # Orchestration engine
│   │   ├── engine.py          # Main ReAct loop
│   │   ├── context.py         # Context manager (sliding window + RAG)
│   │   ├── safety.py          # Safety guardrails & validation
│   │   └── permissions.py     # Permission manifest system
│   ├── llm/                   # LLM adapter layer
│   │   ├── adapter.py         # Unified LLM interface
│   │   ├── ollama.py          # Ollama backend
│   │   └── llamacpp.py        # llama.cpp backend
│   ├── knowledge/             # Knowledge Graph system
│   │   ├── graph.py           # Graph database operations
│   │   ├── entities.py        # Entity definitions (Person, Event, Doc)
│   │   ├── relations.py       # Relationship types
│   │   └── query.py           # Graph query engine
│   ├── sentiment/             # Sentiment Intelligence Engine
│   │   ├── analyzer.py        # Sentiment analysis pipeline
│   │   ├── priority.py        # Priority scoring & escalation
│   │   └── models.py          # Sentiment data models
│   ├── memory/                # Persistent memory system
│   │   ├── manager.py         # Memory lifecycle management
│   │   ├── vectorstore.py     # ChromaDB vector store
│   │   └── embeddings.py      # Local embedding generation
│   ├── plugins/               # Plugin system
│   │   ├── registry.py        # Plugin loader & registry
│   │   ├── base.py            # Base plugin class + @dione_tool decorator
│   │   ├── sandbox.py         # Sandboxed execution environment
│   │   └── builtin/           # Built-in plugins
│   │       ├── gmail.py       # Gmail integration
│   │       ├── whatsapp.py    # WhatsApp reader
│   │       ├── calendar.py    # Calendar management
│   │       ├── filesystem.py  # Local file operations
│   │       └── browser.py     # Browser automation
│   ├── api/                   # API layer
│   │   ├── app.py             # FastAPI application
│   │   ├── routes/            # API routes
│   │   │   ├── chat.py        # Chat endpoints (REST + WebSocket)
│   │   │   ├── knowledge.py   # Knowledge graph endpoints
│   │   │   ├── plugins.py     # Plugin management endpoints
│   │   │   └── status.py      # System status & health
│   │   └── middleware.py      # Auth, CORS, rate limiting
│   ├── config/                # Configuration
│   │   ├── settings.py        # Pydantic settings model
│   │   └── defaults.py        # Default configuration values
│   ├── main.py                # Server entry point
│   ├── requirements.txt       # Python dependencies
│   └── pyproject.toml         # Project metadata
├── mobile/                    # Flutter mobile app
│   └── dione_app/             # Flutter project root
├── docs/                      # Documentation
│   ├── Synopsis .pdf          # Original synopsis
│   ├── ARCHITECTURE.md        # Detailed architecture document
│   └── STAR_FACTORS.md        # Star factor documentation
├── scripts/                   # Utility scripts
│   ├── setup.sh               # One-line setup script
│   └── start.py               # Start Dione server
├── data/                      # Local data directory (gitignored)
│   ├── knowledge/             # Knowledge graph storage
│   ├── vectors/               # ChromaDB vector storage
│   └── memory/                # Persistent memory files
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
├── docker-compose.yml         # Docker setup (optional)
└── README.md                  # This file
```

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd dione

# 2. Install Python dependencies
cd server
pip install -r requirements.txt

# 3. Start Ollama with a local model
ollama pull mistral:7b-instruct

# 4. Configure
cp .env.example .env
# Edit .env with your settings

# 5. Run Dione
python main.py

# 6. Run the mobile app
cd ../mobile/dione_app
flutter run
```

## 👥 Team

| Name | Email |
|------|-------|
| Jass Suraj Shivnani | 2023.jass.shivnani@ves.ac.in |
| Riya Sanjay Khialani | 2023.riya.khialani@ves.ac.in |
| Khushi Sadhuramani | 2023.khushi.sadhuramani@ves.ac.in |
| Ruchika Dingria | 2023.ruchika.dingria@ves.ac.in |

**Guide:** Mrs. Geocey Shejy, Professor, Computer Engineering, V.E.S.I.T

## 📄 License

This project is developed as a Capstone Project (2025-26) at Vivekanand Education Society's Institute of Technology, Department of Computer Engineering.
