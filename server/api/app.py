"""
Dione AI — FastAPI Application

The main FastAPI app that exposes Dione's capabilities
over HTTP and WebSocket for the mobile companion.
"""

from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pathlib import Path

from server.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info("=" * 50)
    logger.info("    DIONE AI — Starting up...")
    logger.info("=" * 50)

    # Initialize all subsystems (stored on app.state)
    from server.memory.manager import MemoryManager
    from server.memory.vectorstore import VectorStore
    from server.memory.embeddings import EmbeddingService
    from server.knowledge.graph import KnowledgeGraph
    from server.sentiment.analyzer import SentimentAnalyzer
    from server.plugins.registry import PluginRegistry
    from server.plugins.integrations import create_default_registry
    from server.core.engine import DioneEngine
    from server.personality.profile import UserProfileManager
    from server.personality.engine import PersonalityEngine
    from server.personality.ui_components import UIDirectiveBuilder
    from server.proactive.heartbeat import HeartbeatScheduler

    # 1. LLM Adapter — pick backend based on config
    logger.info(f"Initializing LLM adapter ({settings.llm.backend})...")
    if settings.llm.backend == "copilot":
        from server.llm.copilot_sdk import CopilotAdapter
        llm = CopilotAdapter(model=settings.llm.model)
    elif settings.llm.backend == "gemini":
        from server.llm.gemini import GeminiAdapter
        llm = GeminiAdapter(
            api_key=settings.llm.api_key,
            model=settings.llm.model,
        )
    elif settings.llm.backend == "openai":
        from server.llm.openai_compat import OpenAIAdapter
        llm = OpenAIAdapter(
            api_key=settings.llm.api_key,
            model=settings.llm.model,
            base_url=settings.llm.api_base_url or "https://api.openai.com/v1",
        )
    elif settings.llm.backend == "ollama":
        from server.llm.ollama import OllamaAdapter
        llm = OllamaAdapter(
            base_url=settings.llm.ollama_host,
            model=settings.llm.model,
        )
    elif settings.llm.backend == "llamacpp":
        from server.llm.llamacpp import LlamaCppAdapter
        llm = LlamaCppAdapter(model_path=settings.llm.llamacpp_path)
    else:
        raise ValueError(f"Unknown LLM backend: {settings.llm.backend}")

    # 2. Embedding Service + Vector Store
    logger.info("Initializing memory system...")
    embeddings = EmbeddingService(model_name=settings.vectorstore.embedding_model)
    vectorstore = VectorStore(
        persist_dir=settings.vectorstore.chroma_path,
        embedding_service=embeddings,
    )
    await vectorstore.initialize()

    # 3. Memory Manager
    memory = MemoryManager(
        data_dir=settings.memory.memory_path,
        vectorstore=vectorstore,
    )
    await memory.initialize()

    # 4. Knowledge Graph
    logger.info("Initializing knowledge graph...")
    knowledge = KnowledgeGraph(storage_path=settings.knowledge.graph_path)
    # Graph auto-loads from disk in __init__

    # 5. Sentiment Analyzer
    logger.info("Initializing sentiment analyzer...")
    sentiment = SentimentAnalyzer(mode=settings.sentiment.model)
    await sentiment.initialize()

    # 6. Plugin Registry
    logger.info("Loading plugins...")
    plugins = PluginRegistry()
    await plugins.load_plugins()

    # 7. User Profile Manager — learns who the user is
    logger.info("Initializing personality systems...")
    profile_manager = UserProfileManager(data_dir="data")

    # 8. Personality Engine — Dione's emotional core
    personality = PersonalityEngine(data_dir="data")

    # 9. UI Directive Builder — AI-controlled UI
    ui_builder = UIDirectiveBuilder()

    # 10. Heartbeat Scheduler — proactive agent
    heartbeat = HeartbeatScheduler(data_dir="data")
    heartbeat.set_profile_manager(profile_manager)
    heartbeat.set_personality_engine(personality)

    # 11. Dione Engine
    logger.info("Assembling Dione Engine (Native ReAct Loop + Safety Kernel)...")
    from server.core.engine import DioneEngine
    engine = DioneEngine()
    engine.set_llm(llm)
    engine.set_plugins(plugins)
    engine.set_knowledge_graph(knowledge)
    engine.set_sentiment_engine(sentiment)
    engine.set_memory_manager(memory)
    engine.set_profile_manager(profile_manager)
    engine.set_personality_engine(personality)
    engine.set_heartbeat(heartbeat)
    engine.set_ui_builder(ui_builder)

    # 12. Integrations (Gmail, Drive, etc.)
    logger.info("Initializing integrations...")
    integrations = create_default_registry(data_dir="data")

    # 13. Telegram Bot Background Service (if token present)
    telegram_token = os.getenv("DIONE_TELEGRAM_BOT_TOKEN", "").strip()
    telegram_service = None
    if telegram_token:
        try:
            logger.info("Initializing Telegram Bot Service...")
            from server.telegram import TelegramBotService
            telegram_service = TelegramBotService(
                bot_token=telegram_token,
                engine=engine,
                allowed_chat_id=os.getenv("DIONE_TELEGRAM_CHAT_ID"),
            )
            started = await telegram_service.start()
            if started:
                logger.info("✨ Telegram Bot Service active: @DioneAiBot")
            app.state.telegram_service = telegram_service
        except Exception as e:
            logger.error(f"Failed to start Telegram service: {e}")

    # Start the heartbeat (background task)
    await heartbeat.start()

    # Store on app state for route access
    app.state.engine = engine
    app.state.llm = llm
    app.state.memory = memory
    app.state.knowledge = knowledge
    app.state.sentiment = sentiment
    app.state.plugins = plugins
    app.state.settings = settings
    app.state.profile = profile_manager
    app.state.personality = personality
    app.state.heartbeat = heartbeat
    app.state.ui_builder = ui_builder
    app.state.integrations = integrations

    logger.info("=" * 50)
    logger.info("    DIONE AI — Ready!")
    logger.info(f"    Model: {settings.llm.model} ({settings.llm.backend})")
    logger.info(f"    Server: http://{settings.server.host}:{settings.server.port}")
    logger.info("=" * 50)

    yield

    # Shutdown
    logger.info("Dione AI shutting down...")
    if telegram_service:
        await telegram_service.stop()
    await heartbeat.stop()
    personality.save()
    profile_manager.save()
    heartbeat.save_patterns()
    knowledge._save()
    await memory.save()
    await llm.close()
    logger.info("Goodbye!")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Dione AI",
        description="Local Large Action Model Orchestration Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow the Flutter mobile app to connect
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from server.api.routes import chat, knowledge, plugins, status, audio, integrations, channels, desktop
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(desktop.router, prefix="/api/desktop", tags=["Desktop"])
    app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
    app.include_router(plugins.router, prefix="/api/plugins", tags=["Plugins"])
    app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
    app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
    app.include_router(status.router, prefix="/api/status", tags=["Status"])
    app.include_router(audio.router, prefix="/api/audio", tags=["Audio"])

    try:
        from server.api.routes import ag_ui
        app.include_router(ag_ui.router, prefix="/api/ag-ui", tags=["AG-UI"])
    except Exception as e:
        logger.debug(f"Optional AG-UI route skipped: {e}")

    # Serve compiled React client SPA if available
    client_dist = Path(__file__).resolve().parent.parent.parent / "client" / "dist"
    if client_dist.exists():
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse
        from starlette.exceptions import HTTPException as StarletteHTTPException

        assets_dir = client_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path.startswith("api"):
                raise StarletteHTTPException(status_code=404, detail="Not Found")
            target = client_dist / full_path
            if target.exists() and target.is_file():
                return FileResponse(target)
            return FileResponse(client_dist / "index.html")
    else:
        @app.get("/", tags=["Root"])
        async def root():
            return {
                "name": "Dione AI",
                "version": "0.2.0",
                "status": "alive",
                "description": "Local Large Action Model Orchestration Engine",
            }

    return app
