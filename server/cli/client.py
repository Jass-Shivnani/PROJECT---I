"""
Dione 2026 — Interactive Multi-Agent CLI & TUI Client
======================================================
A modern 2026 terminal agent studio for Dione AI featuring:
  • Hierarchical Multi-Agent Orchestration DAG tree view (Supervisor -> Sub-Agents)
  • Direct Computer-Use CLI controls (/computer, /screenshot, /click, /type, /launch)
  • Real-Time Neural Voice Talk mode (/voice) with Edge-TTS & Spoken Filler Bridges
  • 5-Tier Safety Kernel status and Blackboard telemetry inspector
"""

import asyncio
import json
import sys
import time
from typing import Optional

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.columns import Columns
from rich.text import Text
from rich import box
import httpx

console = Console(legacy_windows=False)
VERSION = "2026.2.0"

BANNER = """[bold medium_purple1]
  ██████╗ ██╗ ██████╗ ███╗   ██╗███████╗    ██████╗  ██████╗ ██████╗  ██████╗ 
  ██╔══██╗██║██╔═══██╗████╗  ██║██╔════╝    ╚════██╗██╔═████╗╚════██╗██╔════╝ 
  ██║  ██║██║██║   ██║██╔██╗ ██║█████╗       █████╔╝██║██╔██║ █████╔╝███████╗ 
  ██║  ██║██║██║   ██║██║╚██╗██║██╔══╝      ██╔═══╝ ████╔╝██║██╔═══╝ ██╔═══██╗
  ██████╔╝██║╚██████╔╝██║ ╚████║███████╗    ███████╗╚██████╔╝███████╗╚██████╔╝
  ╚═════╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝    ╚══════╝ ╚═════╝ ╚══════╝ ╚═════╝ 
[/bold medium_purple1][dim]  Hierarchical Multi-Agent Orchestrator · Native Computer Use · Neural Voice Talk[/dim]"""

CLIENT_COMMANDS = {
    "/help":       "Show all 2026 Agent CLI commands",
    "/agents":     "Inspect the 6-Agent Orchestration Swarm & capabilities",
    "/dag":        "Render the latest Multi-Agent DAG execution tree & handoffs",
    "/computer":   "Execute direct Computer-Use action (e.g. /computer screenshot, /computer launch spotify)",
    "/voice":      "Toggle real-time Neural Voice Talk synthesis (Edge-TTS + Filler Bridges)",
    "/status":     "Show server, Safety Kernel, & hardware telemetry",
    "/clear":      "Clear terminal viewport",
    "/exit":       "Exit Dione CLI Studio",
}


class DioneClient:
    """2026 Multi-Agent CLI Client for Dione AI."""

    def __init__(self, server_url: str = "http://localhost:8900"):
        self.server_url = server_url.rstrip("/")
        self.history: list[dict] = []
        self.connected = False
        self.voice_enabled = True
        self.computer_use_enabled = True
        self.last_orchestration: Optional[dict] = None

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.server_url}/api/ag-ui/info")
                if resp.status_code == 200:
                    self.connected = True
                    return True
        except Exception:
            pass
        self.connected = False
        return False

    def render_agent_swarm_table(self):
        from server.core.orchestrator import get_multi_agent_orchestrator
        orch = get_multi_agent_orchestrator()
        table = Table(
            title="🤖 Dione 2026 Multi-Agent Orchestration Swarm",
            box=box.ROUNDED,
            border_style="medium_purple1",
            show_lines=True,
        )
        table.add_column("Badge", style="bold cyan", width=8)
        table.add_column("Agent Name", style="bold white", width=28)
        table.add_column("Specialty & Role", style="dim white", width=44)
        table.add_column("Bound Tools", style="green", width=30)

        for a in orch.get_agent_catalog():
            table.add_row(
                f"[{a['badge']}]",
                a["name"],
                a["specialty"],
                ", ".join(a["tools"][:4]) + (f" (+{len(a['tools'])-4})" if len(a["tools"]) > 4 else ""),
            )
        console.print(table)

    def render_dag_tree(self, session_data: dict):
        tree = Tree(
            f"[bold medium_purple1]🕸️ Multi-Agent Execution DAG[/bold medium_purple1] "
            f"[dim](Run: {session_data.get('run_id')} • Total: {session_data.get('total_latency_ms', 0)} ms)[/dim]"
        )
        for node in session_data.get("nodes", []):
            status_icon = "✅" if node["status"] == "completed" else ("🛑" if node["status"] == "blocked" else "⚡")
            branch = tree.add(
                f"{status_icon} [bold cyan][{node['agent_badge']}][/bold cyan] "
                f"[bold white]{node['title']}[/bold white] "
                f"[dim]({node['tool']} • {node['latency_ms']}ms • {node['safety_tier']})[/dim]"
            )
            if node.get("thought"):
                branch.add(f"[italic dim]💭 {node['thought']}[/italic dim]")
            if node.get("output"):
                branch.add(f"[green]↳ {node['output']}[/green]")
        console.print(tree)

    async def execute_goal_local_or_remote(self, prompt: str):
        """Run goal via server /api/ag-ui/orchestrate or local in-process MultiAgentOrchestrator."""
        if await self.check_connection():
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        f"{self.server_url}/api/ag-ui/orchestrate",
                        json={"message": prompt},
                    )
                    if resp.status_code == 200:
                        self.last_orchestration = resp.json()
                        return self.last_orchestration
            except Exception:
                pass

        # In-process fallback so CLI always works standalone
        from server.core.orchestrator import get_multi_agent_orchestrator
        orch = get_multi_agent_orchestrator()
        session = await orch.execute_orchestrated_goal(prompt)
        self.last_orchestration = session.to_dict()
        return self.last_orchestration

    async def run_interactive(self):
        console.print(BANNER)
        is_online = await self.check_connection()
        status_pill = "[bold green]● FastAPI Connected[/bold green]" if is_online else "[bold cyan]● Local In-Process Runtime[/bold cyan]"
        console.print(
            Panel(
                f"{status_pill}  |  [bold medium_purple1]6 Specialized Agents Active[/bold medium_purple1]  |  "
                f"[bold cyan]Computer Use: ON[/bold cyan]  |  [bold emerald]Voice Talk: {'ON' if self.voice_enabled else 'OFF'}[/bold emerald]\n"
                f"[dim]Type a goal to trigger Multi-Agent DAG execution, or type [bold]/help[/bold], [bold]/agents[/bold], [bold]/dag[/bold], [bold]/computer[/bold], [bold]/voice[/bold].[/dim]",
                border_style="medium_purple1",
                box=box.ROUNDED,
            )
        )

        while True:
            try:
                user_input = console.input("\n[bold medium_purple1]dione-2026[/bold medium_purple1] [cyan]❯[/cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Shutting down Dione CLI Studio...[/dim]")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd in ("/exit", "/quit"):
                    break
                elif cmd == "/help":
                    t = Table(title="2026 Agent Studio CLI Commands", box=box.SIMPLE)
                    t.add_column("Command", style="bold cyan")
                    t.add_column("Description", style="white")
                    for k, v in CLIENT_COMMANDS.items():
                        t.add_row(k, v)
                    console.print(t)
                elif cmd == "/agents":
                    self.render_agent_swarm_table()
                elif cmd == "/dag":
                    if self.last_orchestration:
                        self.render_dag_tree(self.last_orchestration)
                    else:
                        console.print("[yellow]No DAG executed yet. Enter a task first![/yellow]")
                elif cmd == "/voice":
                    self.voice_enabled = not self.voice_enabled
                    console.print(f"[bold cyan]🎙️ Neural Voice Talk mode: {'ENABLED' if self.voice_enabled else 'MUTED'}[/bold cyan]")
                elif cmd == "/clear":
                    console.clear()
                    console.print(BANNER)
                elif cmd == "/computer":
                    goal = arg if arg else "Inspect my desktop screen and list open windows"
                    session_data = await self.execute_goal_local_or_remote(goal)
                    self.render_dag_tree(session_data)
                else:
                    console.print(f"[yellow]Unknown command: {cmd}. Type /help for options.[/yellow]")
                continue

            # Standard goal -> Multi-Agent DAG orchestration
            session_data = await self.execute_goal_local_or_remote(user_input)
            self.render_dag_tree(session_data)
            console.print(
                Panel(
                    Markdown(session_data.get("final_synthesis", "Task complete.")),
                    title="[bold green]✨ Supervisor Blackboard Synthesis[/bold green]",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )

            if self.voice_enabled:
                try:
                    from server.core.runtime.voice_frontman import get_voice_frontman
                    frontman = get_voice_frontman()
                    asyncio.create_task(frontman.speak(session_data.get("final_synthesis", ""), is_filler=False))
                except Exception:
                    pass


def run_client(server_url: str = "http://localhost:8900"):
    client = DioneClient(server_url=server_url)
    asyncio.run(client.run_interactive())


if __name__ == "__main__":
    run_client()
