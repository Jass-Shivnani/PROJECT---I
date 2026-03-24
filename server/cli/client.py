"""
Dione AI — Interactive CLI Chat Client
========================================
A rich terminal client for talking to the Dione AI server.

Usage:
    dione client            Open the chat client
    dione client --server http://localhost:8900

Features:
    • Rich formatted responses (markdown, code blocks, tables)
    • Streaming responses via WebSocket
    • Command palette (type '/help' for commands)
    • Conversation history within session
    • Connection status indicator
    • Mood display from server
"""

import asyncio
import json
import sys
import time
from typing import Optional

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.live import Live
    from rich.text import Text
    from rich.spinner import Spinner
    from rich import box
except ImportError:
    print("ERROR: 'rich' is required. Install with: pip install rich")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("ERROR: 'httpx' is required. Install with: pip install httpx")
    sys.exit(1)


console = Console()

VERSION = "0.2.0"

BANNER = """[bold cyan]
     ██████╗ ██╗ ██████╗ ███╗   ██╗███████╗
     ██╔══██╗██║██╔═══██╗████╗  ██║██╔════╝
     ██║  ██║██║██║   ██║██╔██╗ ██║█████╗
     ██║  ██║██║██║   ██║██║╚██╗██║██╔══╝
     ██████╔╝██║╚██████╔╝██║ ╚████║███████╗
     ╚═════╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
[/bold cyan]"""


# ─── Client Commands ──────────────────────────────────────

CLIENT_COMMANDS = {
    "/help":    "Show this help menu",
    "/clear":   "Clear the screen",
    "/status":  "Show server status & connection info",
    "/mood":    "Show Dione's current mood",
    "/ping":    "Ping the server",
    "/history": "Show conversation history this session",
    "/exit":    "Exit the client (also: /quit, Ctrl+C)",
    "/quit":    "Exit the client",
}


class DioneClient:
    """Interactive CLI chat client for Dione AI."""

    def __init__(self, server_url: str = "http://localhost:8900"):
        self.server_url = server_url.rstrip("/")
        self.ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        self.history: list[dict] = []
        self.connected = False
        self.server_info: dict = {}
        self.mood_info: dict = {}

    # ── Connection ────────────────────────────────────────

    async def check_connection(self) -> bool:
        """Check if the Dione server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.server_url}/api/status/info")
                if resp.status_code == 200:
                    self.server_info = resp.json()
                    self.connected = True
                    return True
        except Exception:
            pass
        self.connected = False
        return False

    async def get_mood(self) -> dict:
        """Fetch Dione's current mood from server."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.server_url}/api/status/info")
                if resp.status_code == 200:
                    data = resp.json()
                    self.mood_info = data.get("mood", {})
                    return self.mood_info
        except Exception:
            pass
        return {}

    async def send_message(self, message: str) -> dict:
        """Send a message to Dione via REST endpoint."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.server_url}/api/chat",
                    json={"message": message},
                )
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {"error": f"Server returned {resp.status_code}"}
        except httpx.ConnectError:
            self.connected = False
            return {"error": "Connection lost. Is the server running? Try 'dione start'"}
        except httpx.ReadTimeout:
            return {"error": "Request timed out. The server might be overloaded."}
        except Exception as e:
            return {"error": str(e)}

    async def ping(self) -> float:
        """Ping the server and return latency in ms."""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.server_url}/")
                if resp.status_code == 200:
                    return (time.monotonic() - start) * 1000
        except Exception:
            pass
        return -1

    # ── Display Helpers ───────────────────────────────────

    def _display_response(self, response: dict):
        """Display an AI response with Rich formatting."""
        text = response.get("response", "")
        if not text:
            console.print("[dim]No response received.[/dim]")
            return

        # Show mood indicator if available
        mood = response.get("mood", {})
        mood_label = mood.get("label", "") if mood else ""

        # Render markdown
        try:
            md = Markdown(text)
            mood_tag = f" [dim]({mood_label})[/dim]" if mood_label else ""
            console.print(Panel(
                md,
                title=f"[bold magenta]🌙 Dione[/bold magenta]{mood_tag}",
                border_style="magenta",
                box=box.ROUNDED,
                padding=(1, 2),
            ))
        except Exception:
            # Fallback to plain text
            console.print(f"[magenta]Dione:[/magenta] {text}")

        # Show latency & tools used
        latency = response.get("latency_ms", 0)
        tools = response.get("tools_used", [])
        meta_parts = []
        if latency:
            meta_parts.append(f"{latency:.0f}ms")
        if tools:
            meta_parts.append(f"tools: {', '.join(tools)}")
        if meta_parts:
            console.print(f"[dim]  ⏱ {' | '.join(meta_parts)}[/dim]")

    def _display_user_message(self, message: str):
        """Display the user's message."""
        console.print(Panel(
            Text(message, style="white"),
            title="[bold cyan]You[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 2),
        ))

    def _display_status(self):
        """Display connection/server status."""
        status_color = "green" if self.connected else "red"
        status_text = "Connected" if self.connected else "Disconnected"

        from rich.table import Table
        table = Table(box=box.SIMPLE, show_header=False, border_style="dim")
        table.add_column(style="cyan", width=14)
        table.add_column()

        table.add_row("Server", self.server_url)
        table.add_row("Status", f"[{status_color}]● {status_text}[/{status_color}]")

        if self.server_info:
            table.add_row("Version", self.server_info.get("version", "?"))
            table.add_row("Backend", self.server_info.get("llm", {}).get("backend", "?"))
            table.add_row("Model", self.server_info.get("llm", {}).get("model", "?"))

        if self.mood_info:
            table.add_row("Mood", self.mood_info.get("label", "?"))

        table.add_row("Messages", str(len(self.history)))

        console.print(Panel(table, title="[bold]Server Status[/bold]", border_style="cyan"))

    def _display_help(self):
        """Show available client commands."""
        from rich.table import Table
        table = Table(box=box.SIMPLE, show_header=True, border_style="dim",
                      title="Client Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        for cmd, desc in CLIENT_COMMANDS.items():
            table.add_row(cmd, desc)

        console.print(table)

    def _display_history(self):
        """Show conversation history for this session."""
        if not self.history:
            console.print("[dim]No messages yet this session.[/dim]")
            return

        console.print(f"\n[bold]Session History ({len(self.history)} messages)[/bold]\n")
        for entry in self.history:
            role = entry["role"]
            content = entry["content"]
            if role == "user":
                console.print(f"  [cyan]You:[/cyan] {content[:80]}{'...' if len(content) > 80 else ''}")
            else:
                console.print(f"  [magenta]Dione:[/magenta] {content[:80]}{'...' if len(content) > 80 else ''}")
        console.print()

    # ── Command Handler ───────────────────────────────────

    async def handle_command(self, command: str) -> bool:
        """
        Handle a slash command. Returns True to continue, False to exit.
        """
        cmd = command.strip().lower()

        if cmd in ("/exit", "/quit"):
            return False

        elif cmd == "/help":
            self._display_help()

        elif cmd == "/clear":
            console.clear()
            console.print(BANNER)

        elif cmd == "/status":
            with console.status("[cyan]Checking server...[/cyan]"):
                await self.check_connection()
                await self.get_mood()
            self._display_status()

        elif cmd == "/mood":
            with console.status("[cyan]Fetching mood...[/cyan]"):
                mood = await self.get_mood()
            if mood:
                label = mood.get("label", "unknown")
                energy = mood.get("energy", 0)
                warmth = mood.get("warmth", 0)
                console.print(Panel(
                    f"[bold]{label}[/bold]\n"
                    f"Energy: {'█' * int(energy * 10)}{'░' * (10 - int(energy * 10))} {energy:.0%}\n"
                    f"Warmth: {'█' * int(warmth * 10)}{'░' * (10 - int(warmth * 10))} {warmth:.0%}",
                    title="🌙 Dione's Mood",
                    border_style="magenta",
                ))
            else:
                console.print("[yellow]Could not fetch mood.[/yellow]")

        elif cmd == "/ping":
            latency = await self.ping()
            if latency >= 0:
                console.print(f"[green]Pong! {latency:.0f}ms[/green]")
            else:
                console.print("[red]Server unreachable.[/red]")

        elif cmd == "/history":
            self._display_history()

        else:
            console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
            console.print("[dim]Type /help for available commands.[/dim]")

        return True

    # ── Main Loop ─────────────────────────────────────────

    async def run(self):
        """Main interactive chat loop."""
        console.print(BANNER)
        console.print(f"[dim]  v{VERSION} — Interactive Client[/dim]")
        console.print()

        # Check connection
        with console.status("[cyan]Connecting to Dione server...[/cyan]"):
            connected = await self.check_connection()

        if connected:
            version = self.server_info.get("version", "?")
            backend = self.server_info.get("llm", {}).get("backend", "?")
            model = self.server_info.get("llm", {}).get("model", "?")
            console.print(Panel(
                f"[green]● Connected[/green] to [cyan]{self.server_url}[/cyan]\n"
                f"[dim]Server v{version} • {backend}/{model}[/dim]",
                border_style="green",
                box=box.ROUNDED,
            ))
        else:
            console.print(Panel(
                f"[red]● Cannot reach server[/red] at [cyan]{self.server_url}[/cyan]\n"
                f"[dim]Make sure the server is running: [cyan]dione start[/cyan][/dim]",
                border_style="red",
                box=box.ROUNDED,
            ))
            console.print("[yellow]You can still type messages — they'll be sent when the server is available.[/yellow]")

        console.print(f"[dim]Type a message to chat, or /help for commands. Ctrl+C to exit.[/dim]\n")

        # Chat loop
        while True:
            try:
                # Prompt
                user_input = console.input("[bold cyan]You ›[/bold cyan] ").strip()

                if not user_input:
                    continue

                # Slash commands
                if user_input.startswith("/"):
                    should_continue = await self.handle_command(user_input)
                    if not should_continue:
                        break
                    continue

                # Regular message
                self._display_user_message(user_input)
                self.history.append({"role": "user", "content": user_input})

                # Send to server with spinner
                response = {}
                with console.status("[magenta]Dione is thinking...[/magenta]", spinner="dots"):
                    response = await self.send_message(user_input)

                if "error" in response:
                    console.print(f"[red]Error: {response['error']}[/red]")
                    # Retry connection check
                    if not self.connected:
                        console.print("[dim]Attempting to reconnect...[/dim]")
                        await self.check_connection()
                else:
                    self._display_response(response)
                    self.history.append({
                        "role": "assistant",
                        "content": response.get("response", ""),
                    })

                console.print()  # Spacing

            except KeyboardInterrupt:
                break
            except EOFError:
                break

        # Goodbye
        console.print()
        console.print(Panel(
            "[bold cyan]See you later! 🌙[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        ))


def run_client(server_url: str = "http://localhost:8900"):
    """Entry point for the client command."""
    client = DioneClient(server_url=server_url)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye! 🌙[/cyan]")
