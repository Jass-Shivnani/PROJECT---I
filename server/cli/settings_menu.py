"""
Dione AI — Settings Menu
=========================
View and modify Dione settings from the CLI.

Usage:
    python -m server.cli.settings_menu
    python -m server.main settings
"""

import json
import sys
from pathlib import Path

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

ENV_PATH = Path(".env")
CONFIG_PATH = Path("data/dione_config.json")
PROFILE_PATH = Path("data/user_profile.json")
PERSONALITY_PATH = Path("data/personality_state.json")


def load_config() -> dict:
    """Load current config."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(config: dict):
    """Save config to disk."""
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )


def load_env() -> dict:
    """Parse .env file into dict."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip()
    return env


def save_env(env: dict):
    """Write env dict back to .env file."""
    lines = ["# Dione AI - Configuration", ""]
    for key, val in env.items():
        lines.append(f"{key}={val}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def show_current_settings():
    """Display current settings."""
    config = load_config()
    env = load_env()

    console.print()
    console.print(Panel("[bold]Current Settings[/bold]", title="⚙️  Dione", border_style="cyan"))

    # LLM
    table = Table(title="🧠 LLM Backend", box=box.SIMPLE, border_style="magenta")
    table.add_column("Setting", style="cyan", width=20)
    table.add_column("Value", style="green")
    table.add_row("Backend", env.get("DIONE_LLM_BACKEND", config.get("llm", {}).get("backend", "not set")))
    table.add_row("Model", env.get("DIONE_LLM_MODEL", config.get("llm", {}).get("model", "not set")))
    table.add_row("API Key", "✅ Set" if env.get("DIONE_LLM_API_KEY") else "❌ Not set")
    table.add_row("Max Tokens", str(config.get("llm", {}).get("max_tokens", 2048)))
    table.add_row("Temperature", str(config.get("llm", {}).get("temperature", 0.7)))
    console.print(table)

    # Server
    table2 = Table(title="🖥️ Server", box=box.SIMPLE, border_style="green")
    table2.add_column("Setting", style="cyan", width=20)
    table2.add_column("Value", style="green")
    table2.add_row("Host", env.get("DIONE_HOST", "0.0.0.0"))
    table2.add_row("Port", env.get("DIONE_PORT", "8900"))
    table2.add_row("Debug", env.get("DIONE_DEBUG", "true"))
    console.print(table2)

    # Profile
    profile = {}
    if PROFILE_PATH.exists():
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    
    table3 = Table(title="👤 Profile", box=box.SIMPLE, border_style="yellow")
    table3.add_column("Setting", style="cyan", width=20)
    table3.add_column("Value", style="green")
    table3.add_row("Name", profile.get("name", "User"))
    table3.add_row("Profession", profile.get("profession", "unknown"))
    table3.add_row("Tone", profile.get("preferred_tone", "balanced"))
    table3.add_row("Total Messages", str(profile.get("total_messages", 0)))
    console.print(table3)
    console.print()


def change_llm():
    """Change LLM backend and model."""
    from server.cli.setup import select_llm_backend
    
    llm = select_llm_backend()
    
    env = load_env()
    env["DIONE_LLM_BACKEND"] = llm["backend"]
    env["DIONE_LLM_MODEL"] = llm["model"]
    if llm["api_key"]:
        env["DIONE_LLM_API_KEY"] = llm["api_key"]
    if llm["backend"] == "ollama":
        env["DIONE_LLM_OLLAMA_HOST"] = llm["ollama_host"]
    save_env(env)

    config = load_config()
    config.setdefault("llm", {})
    config["llm"]["backend"] = llm["backend"]
    config["llm"]["model"] = llm["model"]
    save_config(config)

    console.print("[green]✅ LLM settings updated![/green]\n")


def change_server():
    """Change server settings."""
    env = load_env()
    
    host = Prompt.ask("  [cyan]Host[/cyan]", default=env.get("DIONE_HOST", "0.0.0.0"))
    port = IntPrompt.ask("  [cyan]Port[/cyan]", default=int(env.get("DIONE_PORT", "8900")))
    debug = Confirm.ask("  [cyan]Debug mode?[/cyan]", default=env.get("DIONE_DEBUG", "true") == "true")

    env["DIONE_HOST"] = host
    env["DIONE_PORT"] = str(port)
    env["DIONE_DEBUG"] = "true" if debug else "false"
    save_env(env)

    config = load_config()
    config.setdefault("server", {})
    config["server"]["host"] = host
    config["server"]["port"] = port
    config["server"]["debug"] = debug
    save_config(config)

    console.print("[green]✅ Server settings updated![/green]\n")


def change_profile():
    """Change user profile."""
    profile = {}
    if PROFILE_PATH.exists():
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    name = Prompt.ask("  [cyan]Name[/cyan]", default=profile.get("name", "User"))
    profession = Prompt.ask("  [cyan]Profession[/cyan]", default=profile.get("profession", "developer"))
    tone = Prompt.ask(
        "  [cyan]Communication style[/cyan]",
        choices=["formal", "casual", "balanced", "technical"],
        default=profile.get("preferred_tone", "balanced"),
    )

    profile["name"] = name
    profile["profession"] = profession
    profile["preferred_tone"] = tone

    PROFILE_PATH.write_text(
        json.dumps(profile, indent=2) + "\n",
        encoding="utf-8",
    )
    console.print("[green]✅ Profile updated![/green]\n")


def reset_personality():
    """Reset personality state to defaults."""
    if Confirm.ask("  [yellow]Reset Dione's personality and emotional memory?[/yellow]", default=False):
        state = {
            "mood": {
                "energy": 0.6,
                "warmth": 0.7,
                "curiosity": 0.5,
                "confidence": 0.7,
                "playfulness": 0.3,
                "label": "balanced",
            },
            "interaction_count": 0,
            "last_interaction": 0.0,
            "emotional_memories": [],
        }
        PERSONALITY_PATH.write_text(
            json.dumps(state, indent=2) + "\n",
            encoding="utf-8",
        )
        console.print("[green]✅ Personality reset![/green]\n")


def change_llm_params():
    """Change LLM parameters (temperature, max_tokens)."""
    config = load_config()
    llm = config.get("llm", {})

    temp = Prompt.ask(
        "  [cyan]Temperature (0.0-2.0)[/cyan]",
        default=str(llm.get("temperature", 0.7)),
    )
    max_tokens = IntPrompt.ask(
        "  [cyan]Max tokens[/cyan]",
        default=llm.get("max_tokens", 2048),
    )

    config.setdefault("llm", {})
    config["llm"]["temperature"] = float(temp)
    config["llm"]["max_tokens"] = max_tokens
    save_config(config)
    console.print("[green]✅ LLM params updated![/green]\n")


# ─── Main Menu ─────────────────────────────────────────────

MENU = {
    "1": ("View current settings", show_current_settings),
    "2": ("Change LLM backend/model", change_llm),
    "3": ("Change LLM parameters (temp, tokens)", change_llm_params),
    "4": ("Change server settings", change_server),
    "5": ("Change user profile", change_profile),
    "6": ("Reset personality", reset_personality),
    "0": ("Exit", None),
}


def run_settings():
    """Main settings menu loop."""
    console.print()
    console.print(Panel(
        "[bold]Dione AI — Settings[/bold]\n"
        "[dim]Modify your configuration here.[/dim]",
        title="⚙️  Settings",
        border_style="cyan",
        box=box.ROUNDED,
    ))

    while True:
        console.print()
        for key, (label, _) in MENU.items():
            console.print(f"  [cyan]{key}.[/cyan] {label}")
        console.print()

        choice = Prompt.ask("[cyan]Select option[/cyan]", choices=list(MENU.keys()), default="1")

        if choice == "0":
            console.print("[dim]Goodbye! 🌙[/dim]")
            break

        _, func = MENU[choice]
        if func:
            func()


if __name__ == "__main__":
    run_settings()
