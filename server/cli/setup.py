"""
Dione AI — CLI Setup Wizard
============================
Beautiful, menu-driven setup experience using Rich.

Usage:
    python -m server.cli.setup
    python -m server.main setup
"""

import json
import secrets
import sys
import asyncio
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.table import Table
    from rich.text import Text
    from rich import box
except ImportError:
    print("ERROR: 'rich' is required. Install with: pip install rich")
    sys.exit(1)


console = Console()

# ─── ASCII Art ─────────────────────────────────────────────

BANNER = """
[bold cyan]
     ██████╗ ██╗ ██████╗ ███╗   ██╗███████╗
     ██╔══██╗██║██╔═══██╗████╗  ██║██╔════╝
     ██║  ██║██║██║   ██║██╔██╗ ██║█████╗  
     ██║  ██║██║██║   ██║██║╚██╗██║██╔══╝  
     ██████╔╝██║╚██████╔╝██║ ╚████║███████╗
     ╚═════╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
[/bold cyan]
[dim]   Local AI Assistant — Setup Wizard[/dim]
"""

ENV_PATH = Path(".env")
CONFIG_PATH = Path("data/dione_config.json")
DATA_DIR = Path("data")


def show_welcome():
    """Display welcome screen."""
    console.clear()
    console.print(BANNER)
    console.print(Panel(
        "[bold]Welcome to Dione AI Setup![/bold]\n\n"
        "This wizard will help you configure:\n"
        "  [cyan]1.[/cyan] LLM Backend (how Dione thinks)\n"
        "  [cyan]2.[/cyan] Server settings (where Dione lives)\n"
        "  [cyan]3.[/cyan] Your profile (who you are)\n\n"
        "[dim]You can change any of these later with: python -m server.main settings[/dim]",
        title="🌙 Dione Setup",
        border_style="cyan",
        box=box.ROUNDED,
    ))
    console.print()


# ─── LLM Backend Selection ────────────────────────────────

LLM_BACKENDS = {
    "1": {
        "name": "gemini",
        "label": "Google Gemini",
        "desc": "Cloud — Fast, supports audio/vision. Needs API key.",
        "models": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro"],
        "needs_key": True,
    },
    "2": {
        "name": "openai",
        "label": "OpenAI / Compatible",
        "desc": "Cloud — GPT-4, etc. Needs API key.",
        "models": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini"],
        "needs_key": True,
    },
    "3": {
        "name": "ollama",
        "label": "Ollama (Local)",
        "desc": "Local — Runs on your machine. Private, no API key.",
        "models": ["mistral:7b-instruct", "llama3.2:latest", "gemma2:latest", "qwen2.5:latest"],
        "needs_key": False,
    },
    "4": {
        "name": "copilot",
        "label": "GitHub Copilot / Models",
        "desc": "Cloud — Uses Copilot CLI authentication.",
        "models": ["gpt-5-mini", "gpt-5.3-codex", "claude-sonnet-4.6", "gpt-4.1"],
        "needs_key": False,
    },
}


def select_llm_backend() -> dict:
    """Interactive LLM backend selection."""
    console.print(Panel(
        "[bold]Choose how Dione will think[/bold]",
        title="🧠 LLM Backend",
        border_style="magenta",
    ))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
    table.add_column("#", style="bold", width=3)
    table.add_column("Backend", width=25)
    table.add_column("Description", width=50)

    for key, info in LLM_BACKENDS.items():
        table.add_row(key, f"[bold]{info['label']}[/bold]", info["desc"])

    console.print(table)
    console.print()

    choice = Prompt.ask(
        "[cyan]Select backend[/cyan]",
        choices=list(LLM_BACKENDS.keys()),
        default="1",
    )

    backend = LLM_BACKENDS[choice]
    console.print(f"\n  ✅ Selected: [bold green]{backend['label']}[/bold green]\n")

    # Select model
    console.print("  Available models:")
    for i, m in enumerate(backend["models"], 1):
        console.print(f"    [cyan]{i}.[/cyan] {m}")
    console.print()

    model_idx = Prompt.ask(
        "  [cyan]Select model[/cyan]",
        choices=[str(i) for i in range(1, len(backend["models"]) + 1)],
        default="1",
    )
    model = backend["models"][int(model_idx) - 1]
    console.print(f"  ✅ Model: [bold green]{model}[/bold green]\n")

    # API key if needed
    api_key = ""
    if backend["needs_key"]:
        api_key = Prompt.ask(
            f"  [cyan]Enter your {backend['label']} API key[/cyan]",
            password=True,
        )
        if not api_key.strip():
            console.print("  [yellow]⚠ No key provided — you can add it later in .env[/yellow]")

    # Ollama host (if ollama)
    ollama_host = "http://127.0.0.1:11434"
    if backend["name"] == "ollama":
        ollama_host = Prompt.ask(
            "  [cyan]Ollama server URL[/cyan]",
            default="http://127.0.0.1:11434",
        )

    result = {
        "backend": backend["name"],
        "model": model,
        "api_key": api_key,
        "ollama_host": ollama_host,
    }

    if backend["name"] == "copilot":
        try:
            from server.llm.copilot_auth import ensure_copilot_auth
            ensure_copilot_auth()
        except ImportError:
            pass

    return result


# ─── Server Configuration ─────────────────────────────────

def configure_server() -> dict:
    """Configure server settings."""
    console.print(Panel(
        "[bold]Where should Dione listen?[/bold]",
        title="🖥️  Server",
        border_style="green",
    ))
    console.print()

    host = Prompt.ask("  [cyan]Host[/cyan]", default="0.0.0.0")
    port = IntPrompt.ask("  [cyan]Port[/cyan]", default=8900)
    debug = Confirm.ask("  [cyan]Enable debug mode?[/cyan]", default=True)

    console.print(f"\n  ✅ Server: [bold green]{host}:{port}[/bold green]")
    console.print(f"  ✅ Debug: [bold green]{'Yes' if debug else 'No'}[/bold green]\n")

    return {
        "host": host,
        "port": port,
        "debug": debug,
        "secret_key": secrets.token_hex(32),
    }


# ─── User Profile ─────────────────────────────────────────

def configure_profile() -> dict:
    """Quick user profile setup."""
    console.print(Panel(
        "[bold]Tell Dione about yourself[/bold]\n"
        "[dim]You can skip these — Dione will learn over time.[/dim]",
        title="👤 Your Profile",
        border_style="yellow",
    ))
    console.print()

    name = Prompt.ask("  [cyan]Your name[/cyan]", default="User")
    
    # Profession selection
    professions = [
        "developer", "student", "designer", "researcher",
        "manager", "doctor", "writer", "data scientist",
        "devops", "finance", "other",
    ]
    console.print("  Professions:")
    for i, p in enumerate(professions, 1):
        console.print(f"    [cyan]{i:2d}.[/cyan] {p.title()}")
    console.print()
    
    prof_idx = Prompt.ask(
        "  [cyan]Select profession[/cyan]",
        choices=[str(i) for i in range(1, len(professions) + 1)],
        default="1",
    )
    profession = professions[int(prof_idx) - 1]
    
    if profession == "other":
        profession = Prompt.ask("  [cyan]What's your profession?[/cyan]")

    # Communication style
    tone = Prompt.ask(
        "  [cyan]Communication style[/cyan]",
        choices=["formal", "casual", "balanced", "technical"],
        default="balanced",
    )

    console.print(f"\n  ✅ Name: [bold green]{name}[/bold green]")
    console.print(f"  ✅ Profession: [bold green]{profession}[/bold green]")
    console.print(f"  ✅ Tone: [bold green]{tone}[/bold green]\n")

    return {
        "name": name,
        "profession": profession,
        "preferred_tone": tone,
    }


# ─── Generate Config Files ────────────────────────────────

def generate_env(llm: dict, server: dict):
    """Generate .env file."""
    lines = [
        "# Dione AI - Configuration",
        f"# Generated by setup wizard",
        "",
        "# LLM",
        f"DIONE_LLM_BACKEND={llm['backend']}",
        f"DIONE_LLM_MODEL={llm['model']}",
    ]

    if llm["api_key"]:
        lines.append(f"DIONE_LLM_API_KEY={llm['api_key']}")

    if llm["backend"] == "ollama":
        lines.append(f"DIONE_LLM_OLLAMA_HOST={llm['ollama_host']}")

    lines.extend([
        "",
        "# Server",
        f"DIONE_HOST={server['host']}",
        f"DIONE_PORT={server['port']}",
        f"DIONE_DEBUG={'true' if server['debug'] else 'false'}",
        f"DIONE_SECRET_KEY={server['secret_key']}",
    ])

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_config(llm: dict, server: dict, profile: dict):
    """Generate dione_config.json."""
    from datetime import datetime

    config = {
        "$schema": "dione-config-v2",
        "version": "0.2.0",
        "created_at": datetime.now().isoformat(),
        "user": {
            "name": profile["name"],
            "role": profile["profession"].title(),
        },
        "channels": {
            "app": True,
            "web": True,
            "telegram": False,
            "whatsapp": False,
            "discord": False,
        },
        "llm": {
            "backend": llm["backend"],
            "model": llm["model"],
            "max_tokens": 2048,
            "temperature": 0.7,
        },
        "server": {
            "host": server["host"],
            "port": server["port"],
            "debug": server["debug"],
            "secret_key": server["secret_key"],
            "tunnel": {"type": "none", "enabled": False},
        },
        "personality": {
            "style": "adaptive",
            "mood_enabled": True,
            "proactive_enabled": True,
        },
        "plugins": {
            "enabled": {
                "filesystem": True,
                "system": True,
                "web_search": True,
                "code_runner": False,
            },
            "auto_grant_safe_permissions": True,
            "require_confirmation_for_dangerous": True,
        },
        "integrations": {
            "enabled": {},
            "auto_sync": True,
            "sync_interval_minutes": 30,
        },
        "memory": {
            "enabled": True,
            "auto_store_facts": True,
            "weekly_recaps": True,
            "on_this_day": True,
            "prune_after_days": 90,
            "min_importance_to_keep": 0.1,
        },
        "security": {
            "sandbox_enabled": True,
            "require_confirmation_for": ["delete", "send", "execute"],
            "audit_logging": True,
            "max_retries": 3,
        },
        "paths": {
            "data_dir": "data",
            "plugins_dir": "server/plugins/builtin",
            "logs_dir": "data/logs",
        },
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )


def update_user_profile(profile: dict):
    """Update the user_profile.json with setup data."""
    import time

    profile_path = DATA_DIR / "user_profile.json"
    existing = {}
    if profile_path.exists():
        try:
            existing = json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    existing["name"] = profile["name"]
    existing["profession"] = profile["profession"]
    existing["preferred_tone"] = profile["preferred_tone"]
    if "first_seen" not in existing:
        existing["first_seen"] = time.time()
    existing["last_seen"] = time.time()

    profile_path.write_text(
        json.dumps(existing, indent=2) + "\n",
        encoding="utf-8",
    )


# ─── Main Setup Flow ──────────────────────────────────────

def run_setup():
    """Run the complete setup wizard."""
    show_welcome()
    
    if not Confirm.ask("[cyan]Ready to start setup?[/cyan]", default=True):
        console.print("[yellow]Setup cancelled. Run again anytime.[/yellow]")
        return

    console.print()

    # Step 1: LLM Backend
    llm_config = select_llm_backend()

    # Step 2: Server
    server_config = configure_server()

    # Step 3: Profile
    profile_config = configure_profile()

    # Generate files
    console.print(Panel(
        "[bold]Generating configuration...[/bold]",
        title="⚙️  Saving",
        border_style="blue",
    ))

    generate_env(llm_config, server_config)
    console.print("  ✅ Created [bold].env[/bold]")

    generate_config(llm_config, server_config, profile_config)
    console.print("  ✅ Created [bold]data/dione_config.json[/bold]")

    update_user_profile(profile_config)
    console.print("  ✅ Updated [bold]data/user_profile.json[/bold]")

    # Create data directories
    for d in ["data/logs", "data/memory", "data/knowledge", "data/vectorstore", "data/plugins"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    console.print("  ✅ Data directories ready")

    # Summary
    console.print()
    summary = Table(title="Setup Complete!", box=box.ROUNDED, border_style="green")
    summary.add_column("Setting", style="cyan")
    summary.add_column("Value", style="green")
    summary.add_row("LLM Backend", f"{llm_config['backend']} / {llm_config['model']}")
    summary.add_row("Server", f"{server_config['host']}:{server_config['port']}")
    summary.add_row("User", f"{profile_config['name']} ({profile_config['profession']})")
    summary.add_row("API Key", "✅ Set" if llm_config["api_key"] else "❌ Not set")
    console.print(summary)

    console.print()
    console.print(Panel(
        "[bold green]🎉 Setup complete![/bold green]\n\n"
        "Start Dione with:\n"
        "  [cyan]python -m server.main serve[/cyan]\n\n"
        "Change settings anytime:\n"
        "  [cyan]python -m server.main settings[/cyan]\n\n"
        "[dim]Dione will learn more about you as you talk. Have fun! 🌙[/dim]",
        border_style="green",
        box=box.ROUNDED,
    ))


if __name__ == "__main__":
    run_setup()
