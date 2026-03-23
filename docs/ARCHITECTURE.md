# Dione AI — Architecture Document

## 1. System Overview

Dione AI is a **Local Large Action Model (LAM) Orchestration Engine** — a privacy-first personal AI assistant that lives entirely on the user's PC. Unlike cloud-based assistants, Dione performs all inference, memory storage, and action execution locally.

```
┌──────────────────────────────────────────────────────────┐
│                    USER'S PC (Dione's Home)               │
│                                                          │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  Ollama /    │   │  Knowledge   │   │   Memory     │  │
│  │  llama.cpp   │   │  Graph       │   │  (ChromaDB)  │  │
│  │  (Local LLM) │   │  (NetworkX)  │   │              │  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘  │
│         │                  │                   │          │
│  ┌──────┴──────────────────┴───────────────────┴───────┐  │
│  │              DIONE ENGINE (ReAct Loop)               │  │
│  │  Reason → Act → Observe → Repeat                    │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                 │
│  ┌──────────────────────┴──────────────────────────────┐  │
│  │              FastAPI Server (REST + WS)              │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                 │
└─────────────────────────┼─────────────────────────────────┘
                          │ WebSocket / HTTP
                          │
┌─────────────────────────┼─────────────────────────────────┐
│           MOBILE COMPANION (Flutter)                       │
│  ┌──────────────────────┴──────────────────────────────┐  │
│  │  Chat UI   │  Status Dashboard  │  Settings         │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

## 2. Star Factors (Differentiators from OpenClaw)

### Star Factor #1: Offline Knowledge Graph
- **OpenClaw**: Flat markdown files (MEMORY.md, daily logs)
- **Dione**: Typed entity-relation graph (NetworkX) with persistent storage
- Entities: Person, Event, Document, Project, Task, Location, etc.
- Relations: KNOWS, WORKS_WITH, SENT, PART_OF, DEPENDS_ON, etc.
- Enables: "Send that report to the person I met yesterday" — graph traversal resolves ambiguity

### Star Factor #2: Deep Sentiment & Emotional Intelligence
- Multi-axis analysis: Emotion + Urgency + Importance
- 9 emotion labels (joy, trust, anticipation, surprise, fear, sadness, anger, disgust, neutral)
- Priority computation affects notification strategy and response tone
- Dione adapts its personality based on emotional context

### Star Factor #3: Proactive Ambient Agent
- Dione monitors context and proactively suggests actions
- Pattern recognition across conversations over time
- "You have a meeting with Dr. Sharma in 30 minutes — should I pull up last week's notes?"
- Evolving personality that feels genuinely alive

## 3. Component Architecture

### 3.1 Server Core (`server/core/`)

| File | Purpose |
|------|---------|
| `engine.py` | Main ReAct loop — the heart of Dione. Orchestrates reasoning, tool calls, and observations. Max 10 steps per task. |
| `context.py` | Context window management with sliding window, RAG retrieval, and token counting. Priority-based allocation: 30% RAG, 20% KG. |
| `safety.py` | Safety kernel with pattern blocking, confirmation gates, and prompt injection detection. Output sanitization (redacts sensitive data). |
| `permissions.py` | Least-privilege permission system with NONE → READ → WRITE → EXECUTE → FULL levels. JSON manifest persistence. |

### 3.2 Plugin System (`server/plugins/`)

| File | Purpose |
|------|---------|
| `base.py` | `@dione_tool` decorator auto-generates JSON schema from Python functions. `BasePlugin` base class. |
| `registry.py` | Dynamic plugin discovery — scans `builtin/` directory, auto-imports `BasePlugin` subclasses. |
| `sandbox.py` | Sandboxed execution with timeout enforcement and path restrictions. |
| `builtin/filesystem.py` | File operations (list, read, write, search). Write requires confirmation. |
| `builtin/system.py` | System operations (info, run_command, processes, datetime). Commands require confirmation. |

**Adding a new plugin:**
```python
from server.plugins.base import BasePlugin, dione_tool

class MyPlugin(BasePlugin):
    @dione_tool(description="Does something useful")
    async def my_action(self, target: str) -> str:
        """Perform an action on {target}."""
        return f"Done with {target}"
```
Drop it in `server/plugins/builtin/` and it's auto-discovered.

### 3.3 Knowledge Graph (`server/knowledge/`)

| File | Purpose |
|------|---------|
| `entities.py` | Typed entity definitions (Person, Event, Document, Task, etc.) with specialized fields. |
| `relations.py` | 20+ relation types with weight and context metadata. |
| `graph.py` | NetworkX MultiDiGraph with JSON persistence, CRUD, `query_relevant()`, graph analytics. |
| `query.py` | Natural language → graph traversal. Intent detection routes to specialized query methods. |

**Data flow:**
```
User message → Entity extraction (LLM) → Graph storage
                                      ↓
Query time → keyword matching → connection traversal → context enrichment
```

### 3.4 Sentiment Engine (`server/sentiment/`)

| File | Purpose |
|------|---------|
| `models.py` | Data models: SentimentResult, EmotionLabel (9 types), UrgencyLevel (5 tiers). |
| `analyzer.py` | Multi-mode analysis: transformer model (distilbert) or rule-based fallback. Scores urgency, importance, emotion. |

**Scoring axes:**
- **Emotion**: keyword + transformer classification → EmotionLabel
- **Urgency**: keyword weight + caps detection + exclamation analysis → 0.0–1.0
- **Importance**: domain keywords (financial, legal, medical) + action items → 0.0–1.0
- **Priority**: weighted combination → immediate / soon / batch / ignore

### 3.5 LLM Adapter Layer (`server/llm/`)

| File | Purpose |
|------|---------|
| `adapter.py` | Abstract `BaseLLMAdapter` interface. Defines `generate()`, `stream()`, `health_check()`. Builds dynamic system prompt. |
| `ollama.py` | Ollama backend via REST API (`/api/chat`). Supports streaming, model pulling, JSON mode. |
| `llamacpp.py` | Direct llama-cpp-python bindings. Loads GGUF files in-process. ChatML prompt formatting. |

**System prompt is dynamic** — assembled from personality traits, current mood, recent topics, and user preferences. This is what makes Dione feel alive.

### 3.6 Memory System (`server/memory/`)

| File | Purpose |
|------|---------|
| `embeddings.py` | Local embedding generation via sentence-transformers (all-MiniLM-L6-v2, 384 dims). |
| `vectorstore.py` | ChromaDB wrapper with named collections: conversations, documents, knowledge. |
| `manager.py` | Central memory orchestrator combining short-term (sliding window), long-term (vector), episodic (milestones), and semantic (KG). |

**Memory tiers:**
```
┌─────────────────┐
│  Short-term      │  Last N conversation turns (in-memory)
├─────────────────┤
│  Long-term       │  Embedded conversation chunks (ChromaDB)
├─────────────────┤
│  Episodic        │  Significant events: birthdays, milestones (JSON)
├─────────────────┤
│  Semantic        │  Knowledge graph entities and relations (NetworkX)
└─────────────────┘
```

### 3.7 API Layer (`server/api/`)

| File | Purpose |
|------|---------|
| `app.py` | FastAPI application with lifespan management. Initializes all subsystems on startup. CORS enabled for mobile. |
| `routes/chat.py` | WebSocket endpoint for real-time chat. Token streaming. Conversation management. |
| `routes/knowledge.py` | REST endpoints for knowledge graph CRUD. Entity search, relation management. |
| `routes/plugins.py` | REST endpoints for plugin listing, tool execution. |
| `routes/status.py` | Health check, system stats, LLM status, memory stats. |

### 3.8 Mobile Companion (`mobile/dione_app/`)

| File | Purpose |
|------|---------|
| `main.dart` | App entry point. MultiProvider setup (theme, connection, chat). Material 3 theming. |
| `config/server_config.dart` | Server connection URL configuration. |
| `models/chat_message.dart` | Chat message model (sender, content, timestamp, status). |
| `models/dione_status.dart` | Dione server status model (online, model loaded, memory stats). |
| `providers/chat_provider.dart` | WebSocket chat state management. Message history. |
| `providers/connection_provider.dart` | Server connection management (connect, disconnect, health check). |
| `providers/theme_provider.dart` | Dark/light theme switching. |
| `screens/home_screen.dart` | Main screen with bottom nav (Chat, Status, Settings). |
| `screens/chat_screen.dart` | Chat interface with message list, input field, streaming support. |
| `screens/settings_screen.dart` | Server URL config, theme toggle, about info. |
| `widgets/chat_bubble.dart` | Chat bubble widget with sender-specific styling. |
| `widgets/typing_indicator.dart` | Animated typing indicator when Dione is thinking. |

## 4. Data Flow

### Chat Message Flow
```
1. User types message in Flutter app
2. Message sent via WebSocket to FastAPI
3. Engine receives message:
   a. Sentiment analyzer scores emotion/urgency/importance
   b. Knowledge graph queried for relevant context
   c. Vector store queried for similar past conversations (RAG)
   d. Context manager builds enriched prompt
4. LLM generates response (may include tool calls)
5. If tool call detected:
   a. Safety kernel validates the action
   b. Permission manager checks access level
   c. Plugin registry routes to correct tool
   d. Sandbox executes with timeout/path restrictions
   e. Observation fed back to LLM for next step
6. Final response streamed token-by-token via WebSocket
7. Memory manager stores the conversation turn
8. Knowledge graph updated with extracted entities
```

### Knowledge Graph Flow
```
1. Every conversation turn is analyzed for entities
2. Named entities extracted (people, places, events, projects)
3. Relations inferred from context
4. Graph updated incrementally
5. On next query, graph provides contextual awareness:
   - "Who did I meet last week?" → Graph traversal
   - "What's the status of Project X?" → Entity lookup
   - "Remind me about Dr. Sharma" → Relation expansion
```

## 5. Security Architecture

- **Zero-trust execution**: Every tool call validated before execution
- **Confirmation gates**: Destructive operations (write, delete, execute) require user approval
- **Path sandboxing**: File operations restricted to allowed directories
- **Prompt injection detection**: Patterns like "ignore previous instructions" blocked
- **Output sanitization**: API keys, credit card numbers, etc. automatically redacted
- **Local-only**: No data ever leaves the machine. No telemetry. No cloud calls.

## 6. Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| LLM Inference | Ollama / llama.cpp | Local, fast, supports quantized models |
| Server | Python 3.10+ / FastAPI | Async, AI ecosystem, Pydantic validation |
| Knowledge Graph | NetworkX | Lightweight, no external DB needed |
| Vector Store | ChromaDB | Local, persistent, cosine similarity |
| Embeddings | sentence-transformers | Fast CPU inference, 384-dim vectors |
| Mobile | Flutter (Dart) | Cross-platform, beautiful UI, hot reload |
| Communication | WebSocket + REST | Real-time streaming + CRUD operations |

## 7. Directory Structure

```
PROJECT - I/
├── README.md
├── .env.example
├── .gitignore
├── docs/
│   ├── Synopsis.pdf
│   └── ARCHITECTURE.md          ← You are here
├── server/
│   ├── main.py                  ← Entry point (Typer CLI)
│   ├── requirements.txt
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          ← Pydantic settings
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py            ← ReAct loop (THE HEART)
│   │   ├── context.py           ← Context window manager
│   │   ├── safety.py            ← Safety kernel
│   │   └── permissions.py       ← Permission manager
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py              ← @dione_tool decorator
│   │   ├── registry.py          ← Dynamic loader
│   │   ├── sandbox.py           ← Sandboxed executor
│   │   └── builtin/
│   │       ├── __init__.py
│   │       ├── filesystem.py    ← File operations
│   │       └── system.py        ← System operations
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── entities.py          ← Entity types
│   │   ├── relations.py         ← Relation types
│   │   ├── graph.py             ← Knowledge graph
│   │   └── query.py             ← NL query engine
│   ├── sentiment/
│   │   ├── __init__.py
│   │   ├── models.py            ← Sentiment data models
│   │   └── analyzer.py          ← Sentiment analyzer
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── adapter.py           ← Unified LLM interface
│   │   ├── ollama.py            ← Ollama backend
│   │   └── llamacpp.py          ← llama.cpp backend
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── embeddings.py        ← Local embeddings
│   │   ├── vectorstore.py       ← ChromaDB wrapper
│   │   └── manager.py           ← Memory orchestrator
│   └── api/
│       ├── __init__.py
│       ├── app.py               ← FastAPI application
│       └── routes/
│           ├── __init__.py
│           ├── chat.py          ← WebSocket chat
│           ├── knowledge.py     ← KG REST endpoints
│           ├── plugins.py       ← Plugin endpoints
│           └── status.py        ← Health/stats
└── mobile/
    └── dione_app/
        ├── pubspec.yaml
        └── lib/
            ├── main.dart
            ├── config/
            │   └── server_config.dart
            ├── models/
            │   ├── chat_message.dart
            │   └── dione_status.dart
            ├── providers/
            │   ├── chat_provider.dart
            │   ├── connection_provider.dart
            │   └── theme_provider.dart
            ├── screens/
            │   ├── home_screen.dart
            │   ├── chat_screen.dart
            │   └── settings_screen.dart
            └── widgets/
                ├── chat_bubble.dart
                └── typing_indicator.dart
```

## 8. Getting Started

```bash
# 1. Install Ollama
# Download from https://ollama.ai and run:
ollama serve
ollama pull mistral

# 2. Set up the Python server
cd server
pip install -r requirements.txt
cp ../.env.example ../.env

# 3. Start Dione
python -m server.main

# 4. Set up the mobile app
cd mobile/dione_app
flutter pub get
flutter run
```

## 9. Team

| Role | Name | Enrollment |
|------|------|-----------|
| Project Lead | Jaspreet Singh | 03421012022 |
| Member | Mehul Bhatt | 03621012022 |
| Member | Arav Garg | 04821012022 |
| Guide | Dr. Sonika Dahiya | — |

**Institution**: Maharaja Surajmal Institute of Technology (MSIT), New Delhi  
**Programme**: B.Tech CSE, Semester VII  
**Session**: 2025–26
