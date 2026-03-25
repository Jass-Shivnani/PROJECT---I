"""
Dione AI — Master CLI
======================
The single entry point for all Dione operations.

Usage (from project root):
    dione start          Start server (hidden background process)
    dione start -v       Start server (visible terminal)
    dione client         Open the interactive chat client
    dione setup          Run/re-run setup wizard
    dione restart        Restart the server
    dione stop           Stop the running server
    dione status         Show current status
    dione settings       Open settings menu
    dione reset          Full factory reset (DANGEROUS)
    dione reset config   Reset only configuration files
    dione reset profile  Reset only user profile
    dione reset mood     Reset only personality/mood
    dione reset memory   Reset only conversation memory
    dione logs           Show recent logs
    dione check          Check dependencies
    dione version        Show version

Flags:
    --verbose / -v       Enable verbose logging (server in visible window)
    --debug / -d         Enable debug mode (visible + auto-reload)
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import asyncio
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
    from rich.table import Table
    from rich import box
except ImportError:
    print("ERROR: 'rich' is required. Install with: pip install rich")
    sys.exit(1)

try:
    import typer
except ImportError:
    print("ERROR: 'typer' is required. Install with: pip install typer")
    sys.exit(1)


console = Console()

# ─── Paths ─────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ENV_PATH = PROJECT_ROOT / ".env"
CONFIG_PATH = DATA_DIR / "dione_config.json"
PROFILE_PATH = DATA_DIR / "user_profile.json"
PERSONALITY_PATH = DATA_DIR / "personality_state.json"
HABITS_PATH = DATA_DIR / "habits.json"
LOGS_DIR = DATA_DIR / "logs"
MEMORY_DIR = DATA_DIR / "memory"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
VECTORSTORE_DIR = DATA_DIR / "vectorstore"
PID_FILE = DATA_DIR / ".dione.pid"

VERSION = "0.2.0"

BANNER = """[bold cyan]
     ██████╗ ██╗ ██████╗ ███╗   ██╗███████╗
     ██╔══██╗██║██╔═══██╗████╗  ██║██╔════╝
     ██║  ██║██║██║   ██║██╔██╗ ██║█████╗
     ██║  ██║██║██║   ██║██║╚██╗██║██╔══╝
     ██████╔╝██║╚██████╔╝██║ ╚████║███████╗
     ╚═════╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
[/bold cyan][dim]   v{version} — Local AI Assistant[/dim]
""".replace("{version}", VERSION)


# ─── Typer App ─────────────────────────────────────────────

app = typer.Typer(
    name="dione",
    help="Dione AI — Local AI Personal Assistant",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


def _is_first_run() -> bool:
    """Check if this is the first run (no .env or no config)."""
    return not ENV_PATH.exists() or not CONFIG_PATH.exists()


def _is_server_running() -> bool:
    """Check if Dione server is running."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is alive (Windows)
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def _save_pid():
    """Save current PID to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def _clear_pid():
    """Remove PID file."""
    if PID_FILE.exists():
        PID_FILE.unlink()


def _get_log_level(verbose: bool, debug: bool) -> str:
    """Determine log level from flags."""
    if debug:
        return "debug"
    if verbose:
        return "info"
    return "warning"


def _print_whatsapp_qr_in_cli(qr_data: dict):
    """Render WhatsApp QR directly in terminal when available."""
    if not isinstance(qr_data, dict):
        return

    status_value = qr_data.get("status", "unknown")
    terminal_qr = qr_data.get("terminal")

    console.print(f"[cyan]WhatsApp status:[/cyan] {status_value}")

    if isinstance(terminal_qr, str) and terminal_qr.strip():
        console.print("[bold green]Scan this QR in WhatsApp → Linked devices:[/bold green]")
        console.print()
        console.print(terminal_qr)
        console.print()
        return

    if qr_data.get("qr"):
        console.print("[yellow]QR available at /api/integrations/whatsapp/qr[/yellow]")
    else:
        console.print("[yellow]No QR yet. Run: dione integrations sync whatsapp (or wait a few seconds).[/yellow]")


def _wait_for_whatsapp_connected(registry, timeout_seconds: int = 180):
    """Block until WhatsApp reaches connected status or timeout."""
    integration_obj = registry.get_integration("whatsapp")
    if not integration_obj or not hasattr(integration_obj, "get_qr"):
        return

    console.print("[dim]Waiting for WhatsApp to fully connect...[/dim]")
    deadline = time.time() + timeout_seconds
    last_status = None
    qr_shown = False

    while time.time() < deadline:
        qr_data = asyncio.run(integration_obj.get_qr())
        status_value = qr_data.get("status", "unknown") if isinstance(qr_data, dict) else "unknown"

        if status_value != last_status:
            console.print(f"[cyan]WhatsApp status:[/cyan] {status_value}")
            last_status = status_value

        if isinstance(qr_data, dict) and qr_data.get("terminal") and not qr_shown:
            console.print("[bold green]Scan this QR in WhatsApp → Linked devices:[/bold green]")
            console.print()
            console.print(qr_data.get("terminal"))
            console.print()
            qr_shown = True

        if status_value == "connected":
            console.print("[green]WhatsApp fully connected.[/green]")
            return

        time.sleep(1)

    console.print("[yellow]Timed out waiting for WhatsApp connection. Run: dione integrations sync whatsapp[/yellow]")


# ─── Commands ──────────────────────────────────────────────


@app.command()
def start(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output (show server terminal)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug mode (show server terminal + reload)"),
    port: int = typer.Option(None, "--port", "-p", help="Override port"),
    host: str = typer.Option(None, "--host", help="Override host"),
):
    """
    Start Dione AI server as a background process.

    If this is the first run, launches the setup wizard first.
    Server runs hidden by default; use --verbose to see the server terminal.
    After starting, use 'dione client' to chat.
    """
    console.print(BANNER)

    # First run → setup
    if _is_first_run():
        console.print(Panel(
            "[yellow]First time running Dione![/yellow]\n"
            "Let's set things up real quick.",
            title="🌙 Welcome",
            border_style="cyan",
        ))
        console.print()
        from server.cli.setup import run_setup
        run_setup()
        console.print()

        if _is_first_run():
            console.print("[red]Setup was not completed. Run [cyan]dione start[/cyan] again.[/red]")
            return

    # Already running?
    if _is_server_running():
        console.print("[yellow]⚠ Dione is already running![/yellow]")
        console.print("[dim]Use [cyan]dione restart[/cyan] to restart, or [cyan]dione stop[/cyan] to stop.[/dim]")
        console.print("[dim]Use [cyan]dione client[/cyan] to open the chat client.[/dim]")
        return

    # Load config for display
    config = {}
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    _host = host or env.get("DIONE_HOST", "0.0.0.0")
    _port = port or int(env.get("DIONE_PORT", "8900"))
    backend = env.get("DIONE_LLM_BACKEND", config.get("llm", {}).get("backend", "?"))
    model = env.get("DIONE_LLM_MODEL", config.get("llm", {}).get("model", "?"))

    log_level = _get_log_level(verbose, debug)

    # ── Verify Auth for Copilot ──
    if backend == "copilot":
        try:
            from server.llm.copilot_auth import ensure_copilot_auth
            if not ensure_copilot_auth():
                console.print("[red]Cannot start server without authentication.[/red]")
                return
        except ImportError:
            pass  # Will fail later with a proper error message

    # Show startup summary
    table = Table(box=box.SIMPLE, show_header=False, border_style="dim")
    table.add_column(style="cyan", width=12)
    table.add_column(style="green")
    table.add_row("Backend", f"{backend} / {model}")
    table.add_row("Server", f"{_host}:{_port}")
    table.add_row("Mode", "Verbose" if verbose else ("Debug" if debug else "Background"))
    console.print(table)

    # ── Build the server launch command ──
    python_exe = sys.executable
    server_cmd = [
        python_exe, "-m", "uvicorn",
        "server.api.app:create_app",
        "--factory",
        "--host", str(_host),
        "--port", str(_port),
        "--log-level", log_level,
        "--ws-ping-interval", "30",
        "--ws-ping-timeout", "10",
    ]
    if debug:
        server_cmd.append("--reload")

    show_terminal = verbose or debug

    if show_terminal:
        # ── Verbose/Debug: run in a VISIBLE new console window ──
        console.print("[bold green]🚀 Starting Dione (visible terminal)...[/bold green]")
        console.print(f"[dim]   Server terminal will open in a new window.[/dim]")

        # Use CREATE_NEW_CONSOLE to open a visible window
        CREATE_NEW_CONSOLE = 0x00000010
        proc = subprocess.Popen(
            server_cmd,
            cwd=str(PROJECT_ROOT),
            creationflags=CREATE_NEW_CONSOLE,
        )
    else:
        # ── Background: run HIDDEN, no window ──
        console.print("[bold green]🚀 Starting Dione (background)...[/bold green]")

        # Redirect output to log file
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOGS_DIR / "server_output.log"

        CREATE_NO_WINDOW = 0x08000000
        log_handle = open(log_file, "w", encoding="utf-8")
        proc = subprocess.Popen(
            server_cmd,
            cwd=str(PROJECT_ROOT),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
        )

    # ── Save PID and wait for server to be ready ──
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid))

    console.print(f"[dim]   PID: {proc.pid}[/dim]")
    console.print(f"[dim]   API: http://{_host}:{_port}/api[/dim]")
    console.print()

    # Wait for server to be ready (up to 15 seconds)
    console.print("[dim]Waiting for server to be ready...[/dim]")
    import httpx
    ready = False
    for i in range(30):
        time.sleep(0.5)
        # Check if process died
        if proc.poll() is not None:
            console.print(f"[red]Server process exited with code {proc.returncode}.[/red]")
            if not show_terminal:
                console.print(f"[dim]Check logs: {LOGS_DIR / 'server_output.log'}[/dim]")
            _clear_pid()
            return
        try:
            resp = httpx.get(f"http://{'127.0.0.1' if _host == '0.0.0.0' else _host}:{_port}/", timeout=2)
            if resp.status_code == 200:
                ready = True
                break
        except Exception:
            pass

    if ready:
        console.print(Panel(
            f"[bold green]● Server is running[/bold green]\n\n"
            f"  API:  [cyan]http://{_host}:{_port}/api[/cyan]\n"
            f"  WS:   [cyan]ws://{_host}:{_port}/api/chat/ws[/cyan]\n\n"
            f"[dim]Run [bold cyan]dione client[/bold cyan] to start chatting\n"
            f"Run [bold cyan]dione stop[/bold cyan] to stop the server[/dim]",
            title="🌙 Dione AI",
            border_style="green",
            box=box.ROUNDED,
        ))
    else:
        console.print("[yellow]Server is starting up (may take a few more seconds)...[/yellow]")
        console.print(f"[dim]Run [cyan]dione status[/cyan] to check, or [cyan]dione client[/cyan] to connect.[/dim]")


@app.command()
def integrations(
    action: str = typer.Argument("list", help="Action: list, connect, disconnect, sync, grant"),
    integration_id: str = typer.Argument("", help="Integration id (google_mail, google_drive, etc.)"),
):
    """Manage external integrations (Gmail, Drive, etc.) from CLI."""
    from rich.prompt import Prompt
    from server.plugins.integrations import create_default_registry

    registry = create_default_registry(data_dir="data")

    if action == "list":
        table = Table(title="Integrations", box=box.ROUNDED, border_style="cyan")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Permissions")
        for item in registry.list_integrations():
            perms = registry.get_integration(item["id"]).REQUIRED_PERMISSIONS
            table.add_row(
                item["id"],
                item["name"],
                item["status"],
                ", ".join(p.value for p in perms),
            )
        console.print(table)
        console.print("[dim]Use: dione integrations connect <id>[/dim]")
        return

    if not integration_id:
        console.print("[red]Integration id is required for this action.[/red]")
        console.print("[dim]Example: dione integrations connect google_mail[/dim]")
        return

    integration = registry.get_integration(integration_id)
    if not integration:
        console.print(f"[red]Unknown integration: {integration_id}[/red]")
        return

    if action == "grant":
        result = registry.grant_permissions(integration_id)
        if result["failed"]:
            console.print(f"[yellow]Partial grant. Failed: {', '.join(result['failed'])}[/yellow]")
        else:
            console.print(f"[green]Granted permissions for {integration_id}[/green]")
        return

    if action == "connect":
        # Always grant required permissions first
        registry.grant_permissions(integration_id)

        params = {}
        if integration_id == "google_mail":
            console.print("[bold]Gmail login (App Password)[/bold]")
            console.print("[dim]Use Google account with 2FA + App Password.[/dim]")
            params["email"] = Prompt.ask("Gmail address")
            params["app_password"] = Prompt.ask("Gmail App Password", password=True)
        elif integration_id == "google_drive":
            console.print("[bold]Google Drive OAuth login[/bold]")
            console.print("[dim]Provide OAuth client secret JSON from Google Cloud Console.[/dim]")
            params["client_secret_path"] = Prompt.ask(
                "Path to OAuth client JSON",
                default="data/credentials/google_client_secret.json",
            )
        elif integration_id == "whatsapp":
            console.print("[bold]WhatsApp Web bridge login[/bold]")
            console.print("[dim]This starts a local Node.js bridge and generates QR for WhatsApp linking.[/dim]")
            params["reset_session"] = Confirm.ask(
                "Reset existing WhatsApp pairing before connecting? (recommended if messages are stuck)",
                default=True,
            )
            params["dione_port"] = int(Prompt.ask("Dione port", default="8900"))
            params["bridge_port"] = int(Prompt.ask("Bridge port", default="8901"))
            params["allowed_number"] = Prompt.ask(
                "Reply only to this personal number (optional, with country code)",
                default="",
            ).strip()
        else:
            raw = Prompt.ask("Optional JSON params", default="{}")
            try:
                params = json.loads(raw)
            except Exception:
                params = {}

        result = asyncio.run(registry.connect(integration_id, params))
        if result.get("success"):
            console.print(f"[green]Connected: {integration_id}[/green]")
            sync_result = asyncio.run(registry.sync(integration_id))
            if sync_result.get("success"):
                console.print("[green]Initial sync complete.[/green]")
                if integration_id == "whatsapp":
                    integration_obj = registry.get_integration("whatsapp")
                    qr_data = asyncio.run(integration_obj.get_qr()) if integration_obj and hasattr(integration_obj, "get_qr") else {}
                    _print_whatsapp_qr_in_cli(qr_data)
                    _wait_for_whatsapp_connected(registry)
            else:
                console.print(f"[yellow]Connected but sync failed: {sync_result.get('error', 'unknown')}[/yellow]")
        else:
            console.print(f"[red]Connect failed: {result.get('error', 'unknown error')}[/red]")
        return

    if action == "disconnect":
        result = asyncio.run(registry.disconnect(integration_id))
        if result.get("success"):
            console.print(f"[green]Disconnected: {integration_id}[/green]")
        else:
            console.print(f"[red]Disconnect failed: {result.get('error', 'unknown error')}[/red]")
        return

    if action == "sync":
        result = asyncio.run(registry.sync(integration_id))
        if result.get("success"):
            console.print(f"[green]Synced: {integration_id}[/green]")
            console.print_json(json.dumps(result.get("result", {})))
            if integration_id == "whatsapp":
                integration_obj = registry.get_integration("whatsapp")
                qr_data = asyncio.run(integration_obj.get_qr()) if integration_obj and hasattr(integration_obj, "get_qr") else {}
                _print_whatsapp_qr_in_cli(qr_data)
                _wait_for_whatsapp_connected(registry)
        else:
            console.print(f"[red]Sync failed: {result.get('error', 'unknown error')}[/red]")
        return

    console.print(f"[red]Unknown action: {action}[/red]")
    console.print("[dim]Valid actions: list, connect, disconnect, sync, grant[/dim]")
    console.print()


@app.command()
def client(
    server: str = typer.Option(None, "--server", "-s", help="Server URL (e.g. http://localhost:8900)"),
):
    """
    Open the interactive chat client.

    Connects to a running Dione server and lets you chat
    in a rich terminal interface with markdown rendering.
    """
    # Determine server URL
    if not server:
        # Try to get from config
        _port = 8900
        _host = "127.0.0.1"
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "DIONE_PORT":
                        _port = int(v.strip())
                    if k.strip() == "DIONE_HOST":
                        h = v.strip()
                        # For client, use localhost if server binds to 0.0.0.0
                        _host = "127.0.0.1" if h == "0.0.0.0" else h
        server = f"http://{_host}:{_port}"

    from server.cli.client import run_client
    run_client(server_url=server)


@app.command()
def setup():
    """Run the interactive setup wizard (re-run anytime)."""
    console.print(BANNER)
    from server.cli.setup import run_setup
    run_setup()


@app.command()
def settings():
    """Open the settings menu to view and modify configuration."""
    from server.cli.settings_menu import run_settings
    run_settings()


@app.command()
def restart(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Debug mode"),
):
    """Restart the Dione server."""
    console.print("[yellow]🔄 Restarting Dione...[/yellow]")

    # Stop if running
    if _is_server_running():
        stop()
        time.sleep(1)

    # Start again
    start(verbose=verbose, debug=debug, port=None, host=None)


@app.command()
def stop():
    """Stop the running Dione server."""
    if not _is_server_running():
        console.print("[yellow]Dione is not running.[/yellow]")
        _clear_pid()
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]✅ Dione stopped (PID {pid})[/green]")
    except Exception as e:
        console.print(f"[red]Error stopping Dione: {e}[/red]")
    finally:
        _clear_pid()


@app.command()
def status():
    """Show current Dione status."""
    console.print(BANNER)

    running = _is_server_running()
    first_run = _is_first_run()

    # Status
    table = Table(title="Dione Status", box=box.ROUNDED, border_style="cyan")
    table.add_column("Item", style="cyan", width=20)
    table.add_column("Status", width=40)

    table.add_row(
        "Server",
        "[bold green]● Running[/bold green]" if running else "[bold red]● Stopped[/bold red]"
    )
    table.add_row(
        "Setup",
        "[green]✅ Complete[/green]" if not first_run else "[yellow]⚠ Not configured[/yellow]"
    )

    # Config info
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        table.add_row("Backend", config.get("llm", {}).get("backend", "?"))
        table.add_row("Model", config.get("llm", {}).get("model", "?"))
        table.add_row("Port", str(config.get("server", {}).get("port", "?")))

    # Profile info
    if PROFILE_PATH.exists():
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        table.add_row("User", profile.get("name", "Unknown"))
        table.add_row("Profession", profile.get("profession", "unknown"))
        table.add_row("Messages", str(profile.get("total_messages", 0)))

    # Mood
    if PERSONALITY_PATH.exists():
        mood = json.loads(PERSONALITY_PATH.read_text(encoding="utf-8"))
        label = mood.get("mood", {}).get("label", "?")
        table.add_row("Mood", label)

    # Data sizes
    if DATA_DIR.exists():
        data_size = sum(f.stat().st_size for f in DATA_DIR.rglob("*") if f.is_file())
        table.add_row("Data Size", f"{data_size / 1024:.0f} KB")

    console.print(table)


@app.command()
def reset(
    target: str = typer.Argument(
        "all",
        help="What to reset: all, config, profile, mood, memory, knowledge, logs"
    ),
):
    """
    Reset Dione data.

    Targets:
      all       — FULL factory reset (deletes everything)
      config    — Reset .env and dione_config.json only
      profile   — Reset user profile only
      mood      — Reset personality/mood state only
      memory    — Reset conversation memory only
      knowledge — Reset knowledge graph only
      logs      — Clear log files
    """
    console.print()

    targets = {
        "all": {
            "desc": "🔴 FULL FACTORY RESET — deletes ALL data, config, memory, profile",
            "paths": [ENV_PATH, CONFIG_PATH, PROFILE_PATH, PERSONALITY_PATH, HABITS_PATH],
            "dirs": [MEMORY_DIR, KNOWLEDGE_DIR, VECTORSTORE_DIR, LOGS_DIR],
            "danger": True,
        },
        "config": {
            "desc": "Reset .env and dione_config.json (you'll need to run setup again)",
            "paths": [ENV_PATH, CONFIG_PATH],
            "dirs": [],
            "danger": False,
        },
        "profile": {
            "desc": "Reset user profile (name, profession, preferences)",
            "paths": [PROFILE_PATH],
            "dirs": [],
            "danger": False,
        },
        "mood": {
            "desc": "Reset Dione's personality and emotional memory",
            "paths": [PERSONALITY_PATH],
            "dirs": [],
            "danger": False,
        },
        "memory": {
            "desc": "Clear conversation history and vector store",
            "paths": [],
            "dirs": [MEMORY_DIR, VECTORSTORE_DIR],
            "danger": False,
        },
        "knowledge": {
            "desc": "Clear knowledge graph",
            "paths": [],
            "dirs": [KNOWLEDGE_DIR],
            "danger": False,
        },
        "logs": {
            "desc": "Clear log files",
            "paths": [],
            "dirs": [LOGS_DIR],
            "danger": False,
        },
    }

    if target not in targets:
        console.print(f"[red]Unknown target: {target}[/red]")
        console.print(f"[dim]Valid: {', '.join(targets.keys())}[/dim]")
        return

    info = targets[target]

    if info["danger"]:
        console.print(Panel(
            "[bold red]⚠️  DANGER: FULL FACTORY RESET ⚠️[/bold red]\n\n"
            "This will [bold]permanently delete[/bold]:\n"
            "  • All configuration files (.env, config)\n"
            "  • User profile and preferences\n"
            "  • All conversation history\n"
            "  • All memories and learned knowledge\n"
            "  • Personality and emotional memory\n"
            "  • All log files\n\n"
            "[yellow]This action CANNOT be undone.[/yellow]",
            title="⛔ Factory Reset",
            border_style="red",
            box=box.HEAVY,
        ))
        console.print()

        if not Confirm.ask("[bold red]Are you ABSOLUTELY sure?[/bold red]", default=False):
            console.print("[green]Reset cancelled.[/green]")
            return

        # Double confirm for full reset
        console.print()
        if not Confirm.ask("[bold red]Type 'yes' one more time to confirm[/bold red]", default=False):
            console.print("[green]Reset cancelled.[/green]")
            return
    else:
        console.print(f"[yellow]{info['desc']}[/yellow]")
        if not Confirm.ask("[yellow]Continue?[/yellow]", default=False):
            console.print("[green]Cancelled.[/green]")
            return

    # Perform reset
    deleted = 0
    for p in info["paths"]:
        if p.exists():
            p.unlink()
            deleted += 1
            console.print(f"  🗑️  Deleted {p.name}")

    for d in info["dirs"]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)  # Recreate empty
            deleted += 1
            console.print(f"  🗑️  Cleared {d.name}/")

    if target == "mood":
        # Write fresh defaults
        PERSONALITY_PATH.parent.mkdir(parents=True, exist_ok=True)
        PERSONALITY_PATH.write_text(json.dumps({
            "mood": {"energy": 0.6, "warmth": 0.7, "curiosity": 0.5,
                     "confidence": 0.7, "playfulness": 0.3, "label": "balanced"},
            "interaction_count": 0, "last_interaction": 0.0, "emotional_memories": [],
        }, indent=2), encoding="utf-8")
        console.print("  ✅ Reset mood to defaults")

    console.print(f"\n[green]✅ Reset complete ({deleted} items cleared)[/green]")

    if target in ("all", "config"):
        console.print("[dim]Run [cyan]dione start[/cyan] to set up again.[/dim]")


@app.command()
def logs(
    n: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
):
    """Show recent log files."""
    if not LOGS_DIR.exists():
        console.print("[yellow]No logs found.[/yellow]")
        return

    log_files = sorted(LOGS_DIR.glob("dione_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not log_files:
        fallback = LOGS_DIR / "server_output.log"
        if fallback.exists():
            log_files = [fallback]
        else:
            console.print("[yellow]No log files found.[/yellow]")
            return

    latest = log_files[0]
    console.print(f"[dim]Showing: {latest.name}[/dim]\n")

    lines = latest.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-n:]:
        # Colorize log levels
        if "ERROR" in line:
            console.print(f"[red]{line}[/red]")
        elif "WARNING" in line:
            console.print(f"[yellow]{line}[/yellow]")
        elif "INFO" in line:
            console.print(f"[dim]{line}[/dim]")
        else:
            console.print(line)


@app.command()
def check():
    """Check if all dependencies are installed."""
    console.print(BANNER)
    console.print("[bold]Checking dependencies...[/bold]\n")

    import importlib

    checks = {
        "FastAPI": "fastapi",
        "Uvicorn": "uvicorn",
        "Rich": "rich",
        "Typer": "typer",
        "HTTPX": "httpx",
        "ChromaDB": "chromadb",
        "Sentence Transformers": "sentence_transformers",
        "NetworkX": "networkx",
        "Loguru": "loguru",
        "Pydantic": "pydantic",
        "Tiktoken": "tiktoken",
        "Google GenAI": "google.genai",
        "GitHub Copilot SDK": "copilot",
    }

    all_ok = True
    for name, module in checks.items():
        try:
            importlib.import_module(module)
            console.print(f"  [green]✓[/green] {name}")
        except ImportError:
            console.print(f"  [red]✗[/red] {name} — [dim]not installed[/dim]")
            all_ok = False

    console.print()
    if all_ok:
        console.print("[bold green]All checks passed! ✅[/bold green]")
    else:
        console.print("[yellow]Some dependencies missing. Install with:[/yellow]")
        console.print("[cyan]  pip install -r server/requirements.txt[/cyan]")


@app.command()
def version():
    """Show Dione version."""
    console.print(f"Dione AI v{VERSION}")


# ─── Module entry point ───────────────────────────────────

if __name__ == "__main__":
    # Ensure we're in the project root
    os.chdir(str(PROJECT_ROOT))
    app()
