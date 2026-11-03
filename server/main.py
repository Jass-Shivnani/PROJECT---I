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

import sys
import typer
import uvicorn
from loguru import logger
from pathlib import Path

# Ensure UTF-8 output and stable asyncio event loop on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

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
        encoding="utf-8",
    )
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        colorize=True,
    )

    # Ensure data directories exist
    for dir_name in ["data/logs", "data/memory", "data/knowledge", "data/vectorstore", "data/plugins"]:
        Path(dir_name).mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting Dione AI on {_host}:{_port}")

    loop_type = "asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto"

    uvicorn.run(
        "server.api.app:create_app",
        factory=True,
        host=_host,
        port=_port,
        reload=reload,
        log_level=log_level,
        loop=loop_type,
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
            typer.echo(f"  [OK] {name}")
        except ImportError:
            typer.echo(f"  [MISSING] {name} - NOT INSTALLED")
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
        typer.echo("  [OK] Ollama server")
    else:
        typer.echo("  [OPTIONAL] Ollama server - NOT RUNNING (start with: ollama serve if using offline models)")

    if all_ok:
        typer.echo("\n  All checks passed! Run: python -m server.main serve")
    else:
        typer.echo("\n  Some checks failed. Install missing deps: pip install -r server/requirements.txt")


@app.command()
def version():
    """Show Dione AI version."""
    typer.echo("Dione AI v0.2.0")


@app.command()
def setup():
    """Run the interactive setup wizard."""
    from server.cli.setup import run_setup
    run_setup()


@app.command()
def settings():
    """Open the settings menu to view/modify configuration."""
    from server.cli.settings_menu import run_settings
    run_settings()


def _auto_detect_first_run():
    """If no .env exists, suggest running setup."""
    env_path = Path(".env")
    if not env_path.exists():
        from rich.console import Console
        console = Console()
        console.print(
            "\n  [yellow]⚠ No .env file found![/yellow]\n"
            "  Looks like this is your first time running Dione.\n"
            "  Run the setup wizard first:\n\n"
            "    [cyan]python -m server.main setup[/cyan]\n"
        )


if __name__ == "__main__":
    _auto_detect_first_run()
    app()
