"""
Dione AI — Copilot SDK Authentication Helper

Checks and enforces GitHub Copilot OAuth authentication before server startup.
If the user is not authenticated, it runs `copilot login` to start the device flow.
"""

import sys
import asyncio
import subprocess
from rich.console import Console

console = Console()

def ensure_copilot_auth():
    """
    Checks if GitHub Copilot is authenticated.
    If not, starts the OAuth device login flow interactively.
    """
    try:
        from copilot import CopilotClient
        from copilot.types import SubprocessConfig
        from copilot.client import _get_bundled_cli_path
    except ImportError:
        # If not installed, wait for the actual adapter import to throw the error
        # with instructions to pip install
        return True

    # Check authentication
    async def _check():
        config = SubprocessConfig()
        config.use_logged_in_user = True
        config.log_level = 'error'
        client = CopilotClient(config)
        await client.start()
        auth = await client.get_auth_status()
        await client.stop()
        return getattr(auth, "isAuthenticated", False)

    try:
        is_auth = asyncio.run(_check())
    except Exception as e:
        console.print(f"[yellow]Warning: Could not check Copilot auth status: {e}[/yellow]")
        return True

    if is_auth:
        return True

    # Not authenticated — Start OAuth device flow!
    console.print("\n[bold cyan]GitHub Copilot is not authenticated.[/bold cyan]")
    console.print("Starting OAuth device flow to log you in...\n")
    
    cli_path = _get_bundled_cli_path()
    if not cli_path:
        console.print("[red]Error: Could not find bundled Copilot CLI.[/red]")
        return False

    try:
        # Run interactive login process (blocks until user finishes)
        result = subprocess.run([cli_path, "login"], check=False)
        if result.returncode == 0:
            console.print("[green]Successfully authenticated with GitHub Copilot![/green]\n")
            return True
        else:
            console.print("[red]Authentication failed or was cancelled.[/red]\n")
            return False
    except FileNotFoundError:
        console.print(f"[red]Error: Found CLI path {cli_path} but file does not exist.[/red]")
        return False
    except KeyboardInterrupt:
        console.print("\n[yellow]Authentication cancelled by user.[/yellow]\n")
        return False

if __name__ == "__main__":
    ensure_copilot_auth()
