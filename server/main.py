"""
╔══════════════════════════════════════════════════════════╗
║                      DIONE AI                            ║
║    Local Large Action Model Orchestration Engine         ║
║                                                          ║
║    "She lives on your machine. She remembers.            ║
║     She learns. She acts. She feels alive."              ║
╚══════════════════════════════════════════════════════════╝

Entry point for the Dione AI server.

Usage:
    python -m server.main                  # Default (0.0.0.0:8000)
    python -m server.main --port 9000      # Custom port
    python -m server.main --reload         # Dev mode with hot reload
"""

import typer
import uvicorn
from loguru import logger
from pathlib import Path

from server.config.settings import get_settings

app = typer.Typer(
    name="dione",
    help="Dione AI — Local Large Action Model Engine",
)


@app.command()
def serve(
    host: str = typer.Option(None, help="Host to bind to"),
    port: int = typer.Option(None, help="Port to listen on"),
    reload: bool = typer.Option(False, help="Enable auto-reload (dev mode)"),
    log_level: str = typer.Option("info", help="Log level"),
):
    """Start the Dione AI server."""
    settings = get_settings()

    _host = host or settings.server.host
    _port = port or settings.server.port

    # Configure logging
    logger.remove()
    logger.add(
        "data/logs/dione_{time}.log",
        rotation="10 MB",
        retention="7 days",
        level=log_level.upper(),
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level=log_level.upper(),
        colorize=True,
    )

    # Ensure data directories exist
    for dir_name in ["data/logs", "data/memory", "data/knowledge", "data/vectorstore", "data/plugins"]:
        Path(dir_name).mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting Dione AI on {_host}:{_port}")

    uvicorn.run(
        "server.api.app:create_app",
        factory=True,
        host=_host,
        port=_port,
        reload=reload,
        log_level=log_level,
        ws_ping_interval=30,
        ws_ping_timeout=10,
    )


@app.command()
def check():
    """Check if all dependencies and models are available."""
    import importlib

    checks = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "httpx": "httpx",
        "chromadb": "chromadb",
        "sentence_transformers": "sentence_transformers",
        "networkx": "networkx",
        "loguru": "loguru",
        "pydantic": "pydantic",
        "tiktoken": "tiktoken",
    }

    all_ok = True
    for name, module in checks.items():
        try:
            importlib.import_module(module)
            typer.echo(f"  ✓ {name}")
        except ImportError:
            typer.echo(f"  ✗ {name} — NOT INSTALLED")
            all_ok = False

    # Check Ollama
    import asyncio
    from server.llm.ollama import OllamaAdapter

    async def _check_ollama():
        adapter = OllamaAdapter()
        healthy = await adapter.health_check()
        await adapter.close()
        return healthy

    ollama_ok = asyncio.run(_check_ollama())
    if ollama_ok:
        typer.echo("  ✓ Ollama server")
    else:
        typer.echo("  ✗ Ollama server — NOT RUNNING (start with: ollama serve)")
        all_ok = False

    if all_ok:
        typer.echo("\n  All checks passed! Run: python -m server.main serve")
    else:
        typer.echo("\n  Some checks failed. Install missing deps: pip install -r server/requirements.txt")


@app.command()
def version():
    """Show Dione AI version."""
    typer.echo("Dione AI v0.1.0")


if __name__ == "__main__":
    app()
