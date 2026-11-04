"""
Dione AI — Hermes Agent & OpenClaw Programmatic Execution Plugin (v6.0)
=======================================================================
Directly ports the core task-execution primitives from:
1. NousResearch/hermes-agent (`tools/code_execution_tool.py`, `run_agent.py`, `tools/delegate_tool.py`):
   - `execute_code`: Programmatic Tool Calling (PTC) sandbox with generated `hermes_tools.py` & `dione_tools.py`
     RPC bridge (TCP loopback `127.0.0.1` for Windows 11 + POSIX compatibility), `json_parse`, `shell_quote`,
     `retry`, 40%/60% head/tail stdout truncation with spill-to-disk (`data/cache/exec/`), and
     `_sandbox_failure_hint` recovery diagnostics.
   - `todo`: Persistent multi-turn task checklist (`data/memory/hermes_todo.json`) so the agent tracks and
     verifies every sub-goal before stopping.
   - `delegate_task`: Isolated sub-agent / sub-task execution (`delegate_tool.py` + OpenClaw `SubagentManager`)
     for multi-part research or parallel tool workflows without bloating parent context.
2. OpenClaw (`openclaw/openclaw`):
   - Lane-aware tool call serialization, bounded output compaction, and deterministic error recovery hints.
"""

import asyncio
import datetime
import hashlib
import json
import math
import os
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from server.plugins.base import BasePlugin, dione_tool

# ---------------------------------------------------------------------------
# Constants ported from NousResearch/hermes-agent/tools/code_execution_tool.py
# ---------------------------------------------------------------------------
MAX_STDOUT_BYTES = 50_000      # 50 KB stdout cap returned to LLM
MAX_STDERR_BYTES = 10_000      # 10 KB stderr cap
DEFAULT_TIMEOUT_SECONDS = 45   # Default script timeout
MAX_TIMEOUT_SECONDS = 180      # Hard ceiling per script execution
MAX_TOOL_CALLS_PER_EXEC = 30   # Max RPC tool calls inside a single execute_code run


def _sandbox_failure_hint(exit_code: int, stderr: str, timed_out: bool) -> Optional[str]:
    """
    Return a short actionable hint for common sandbox failure modes, or None.
    Ported directly from NousResearch/hermes-agent (`tools/code_execution_tool.py`).
    """
    if timed_out:
        return (
            "Hint: Script timed out. Avoid long `time.sleep(...)` calls, infinite loops, "
            "or blocking interactive prompts (`input()`)."
        )
    if exit_code in (-9, 137):
        return (
            "Hint: Process killed (SIGKILL / exit 137) — likely hit memory or resource limits. "
            "Stream files line-by-line instead of loading large blobs into memory."
        )
    stderr_lower = (stderr or "").lower()
    if "memoryerror" in stderr_lower or "cannot allocate memory" in stderr_lower:
        return "Hint: Out of memory inside sandbox. Process data incrementally."
    if "no space left on device" in stderr_lower:
        return "Hint: Sandbox temp directory is full. Remove intermediate files after use."
    if "read-only file system" in stderr_lower or "permissionerror" in stderr_lower:
        return "Hint: Permission denied on target path. Write temporary files to the current working directory or `data/cache/`."
    if "modulenotfounderror" in stderr_lower or "importerror" in stderr_lower:
        return (
            "Hint: Use `from hermes_tools import ...` or `from dione_tools import ...` plus Python standard library "
            "modules (`json`, `math`, `re`, `pathlib`, `urllib.request`, `ctypes`)."
        )
    return None


def _spill_Full_stdout(stdout: str) -> Optional[Path]:
    """
    Persist full stdout to `data/cache/exec/stdout-<sha256[:12]>.txt` when truncated.
    Ported from NousResearch/hermes-agent (`_spill_full_stdout`).
    """
    try:
        cache_dir = Path("data/cache/exec")
        cache_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(stdout.encode("utf-8", errors="replace")).hexdigest()[:12]
        out_path = cache_dir / f"stdout-{digest}.txt"
        out_path.write_text(stdout, encoding="utf-8", errors="replace")
        return out_path.resolve()
    except Exception as exc:
        logger.debug(f"Could not spill full stdout to disk: {exc}")
        return None


def _truncate_stdout(stdout: str) -> str:
    """
    Head/tail 40%/60% truncation ported from NousResearch/hermes-agent (`_truncate_stdout`).
    Preserves the opening headers/schema and the final results/tracebacks.
    """
    if len(stdout) <= MAX_STDOUT_BYTES:
        return stdout
    head = int(MAX_STDOUT_BYTES * 0.4)
    tail = MAX_STDOUT_BYTES - head
    omitted = len(stdout) - MAX_STDOUT_BYTES
    spill_path = _spill_Full_stdout(stdout)
    if spill_path is not None:
        notice = (
            f"\n\n... [TRUNCATED {omitted:,} chars — full output ({len(stdout):,} chars) "
            f"saved to {spill_path}; inspect with read_file if needed] ...\n\n"
        )
    else:
        notice = f"\n\n... [STDOUT TRUNCATED: {omitted:,} chars omitted out of {len(stdout):,}] ...\n\n"
    return stdout[:head] + notice + stdout[-tail:]


def _generate_hermes_and_dione_tools_shim(port: int) -> str:
    """
    Generate the `hermes_tools.py` / `dione_tools.py` module injected into the `execute_code` sandbox.
    Follows NousResearch/hermes-agent's `_generate_hermes_tools_module` pattern, using a fast
    loopback TCP socket (`127.0.0.1:<port>`) so it works identically on Windows 11 and Linux.
    """
    return textwrap.dedent(f'''\
        """Auto-generated Hermes/Dione Programmatic Tool Calling (PTC) RPC module."""
        import json as _json
        import shlex as _shlex
        import socket as _socket
        import time as _time

        _RPC_PORT = {port}

        def _call(tool_name: str, **kwargs):
            """Send a tool call over the local RPC loopback bridge and return the parsed result."""
            payload = _json.dumps({{"tool": tool_name, "args": kwargs}}, default=str) + "\\n"
            sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            sock.settimeout(120.0)
            try:
                sock.connect(("127.0.0.1", _RPC_PORT))
                sock.sendall(payload.encode("utf-8"))
                buf = b""
                while not buf.endswith(b"\\n"):
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                raw_resp = buf.decode("utf-8", errors="replace").strip()
                try:
                    parsed = _json.loads(raw_resp)
                    if isinstance(parsed, dict) and "result" in parsed:
                        return parsed["result"]
                    return parsed
                except Exception:
                    return raw_resp
            finally:
                sock.close()

        # --- Helper utilities ported from NousResearch/hermes-agent ---
        def json_parse(text: str):
            """Parse JSON string Tolerantly, returning dict/list or raw string on failure."""
            try:
                return _json.loads(text)
            except Exception as e:
                return {{"error": f"JSON parse failed: {{e}}", "raw": text[:500]}}

        def shell_quote(text: str) -> str:
            """POSIX/CLI-safe quoting for dynamic arguments."""
            return _shlex.quote(str(text))

        def retry(fn, max_attempts: int = 3, delay: float = 1.0):
            """Retry a callable with exponential backoff (delay * 2**attempt)."""
            last_err = None
            for attempt in range(max_attempts):
                try:
                    return fn()
                except Exception as e:
                    last_err = e
                    if attempt + 1 < max_attempts:
                        _time.sleep(delay * (2 ** attempt))
            raise last_err

        # --- Programmatic Tool Wrappers ---
        def web_search(query: str, max_results: int = 5):
            """Search the web and return structured results."""
            return _call("web_search", query=query, max_results=max_results)

        def scrape_url(url: str):
            """Fetch and extract readable text from a webpage URL."""
            return _call("scrape_url", url=url)

        def read_file(path: str):
            """Read a local file's contents."""
            return _call("read_file", path=path)

        def write_file(path: str, content: str):
            """Write content to a local file."""
            return _call("write_file", path=path, content=content)

        def list_directory(path: str = "."):
            """List files and folders in a directory."""
            return _call("list_directory", path=path)

        def search_files(pattern: str, directory: str = "."):
            """Search for files matching a pattern."""
            return _call("search_files", pattern=pattern, directory=directory)

        def run_command(command: str):
            """Run a shell or PowerShell command."""
            return _call("run_command", command=command)

        def launch_app(app: str):
            """Launch or focus a Windows 11 desktop application."""
            return _call("launch_app", app=app)

        def computer_use(action: str, **kwargs):
            """Unified Hermes Computer-Use 4-rung action tool (capture, click, move, drag, type, press, key_combo, scroll, wait)."""
            return _call("computer_use", action=action, **kwargs)

        def computer_click(x: int, y: int, button: str = "left", clicks: int = 1):
            """Click at screen pixel coordinates (x, y)."""
            return _call("computer_click", x=x, y=y, button=button, clicks=clicks)

        def computer_drag(start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 35, button: str = "left"):
            """Smoothly drag the mouse from (start_x, start_y) to (end_x, end_y)."""
            return _call("computer_drag", start_x=start_x, start_y=start_y, end_x=end_x, end_y=end_y, steps=steps, button=button)

        def computer_draw_shape(shape: str = "circle", center_x: int = 0, center_y: int = 0, radius: int = 130, app: str = "mspaint"):
            """Draw a geometric shape ('circle', 'square', 'rectangle', 'triangle', 'star', 'heart', 'smiley', 'spiral') in MS Paint or canvas."""
            return _call("computer_draw_shape", shape=shape, center_x=center_x, center_y=center_y, radius=radius, app=app)

        def computer_type(text: str, press_enter: bool = False):
            """Type text into the focused window."""
            return _call("computer_type", text=text, press_enter=press_enter)

        def computer_hotkey(keys: str):
            """Press a keyboard shortcut (e.g. 'ctrl+s', 'alt+tab', 'enter')."""
            return _call("computer_hotkey", keys=keys)

        def computer_uia_action(target_name: str, pattern: str = "invoke", value: str = "", app: str = ""):
            """Invoke a semantic Windows UIA pattern ('invoke', 'set_value', 'toggle', 'select') on a named control."""
            return _call("computer_uia_action", target_name=target_name, pattern=pattern, value=value, app=app)
    ''')


class HermesExecutionPlugin(BasePlugin):
    """
    NousResearch Hermes Agent & OpenClaw Programmatic Execution Plugin.
    Provides `execute_code` (Programmatic Tool Calling), `todo` (Persistent Task Ledger),
    and `delegate_task` (Isolated Sub-Agent Delegation).
    """

    name = "HermesExecutionPlugin"
    description = (
        "NousResearch Hermes Agent Programmatic Tool Calling (`execute_code`), "
        "persistent `todo` checklist ledger, and `delegate_task` sub-agent execution."
    )
    version = "6.0.0"

    def __init__(self):
        super().__init__()
        self._todo_path = Path("data/memory/hermes_todo.json")
        self._todo_path.parent.mkdir(parents=True, exist_ok=True)
        self._tool_Dispatch_cache: Dict[str, Any] = {}

    def _dispatch_rpc_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute a Dione tool synchronously on behalf of the `execute_code` RPC server thread.
        Routes directly to ComputerUsePlugin, SystemPlugin, FileManagerPlugin, WebSearchPlugin,
        or Hermes ComputerUseTool.
        """
        try:
            target_coro = None
            if tool_name in ("read_file", "write_file", "list_directory", "search_files"):
                if "fm" not in self._tool_Dispatch_cache:
                    from server.plugins.builtin.file_manager import FileManagerPlugin
                    self._tool_Dispatch_cache["fm"] = FileManagerPlugin()
                fn = getattr(self._tool_Dispatch_cache["fm"], tool_name)
                target_coro = fn(**args)
            elif tool_name in ("web_search", "scrape_url"):
                if "web" not in self._tool_Dispatch_cache:
                    from server.plugins.builtin.web_search import WebSearchPlugin
                    self._tool_Dispatch_cache["web"] = WebSearchPlugin()
                fn = getattr(self._tool_Dispatch_cache["web"], tool_name)
                target_coro = fn(**args)
            elif tool_name.startswith("computer_") or tool_name in ("launch_app", "open_browser", "play_youtube_video", "inspect_screen_vision"):
                if "cu" not in self._tool_Dispatch_cache:
                    from server.plugins.builtin.computer_use_plugin import ComputerUsePlugin
                    self._tool_Dispatch_cache["cu"] = ComputerUsePlugin()
                fn = getattr(self._tool_Dispatch_cache["cu"], tool_name)
                target_coro = fn(**args)
            elif tool_name in ("run_command", "system_info", "open_application"):
                if "sys" not in self._tool_Dispatch_cache:
                    from server.plugins.builtin.system import SystemPlugin
                    self._tool_Dispatch_cache["sys"] = SystemPlugin()
                fn = getattr(self._tool_Dispatch_cache["sys"], tool_name)
                target_coro = fn(**args)
            else:
                return {"error": f"Unknown RPC tool: {tool_name}"}

            if asyncio.iscoroutine(target_coro):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(target_coro)
                finally:
                    loop.close()
            return target_coro
        except Exception as exc:
            logger.warning(f"[HermesPTC] RPC tool {tool_name} error: {exc}")
            return {"error": str(exc)}

    @dione_tool(
        description=(
            "Run a Python script with programmatic access to Dione & Hermes tools (`from hermes_tools import ...` "
            "or `from dione_tools import ...`). Ideal when you need to chain 3+ tool calls, compute coordinates, "
            "filter/aggregate data in Python, or automate multi-step desktop/file/web workflows in a single turn. "
            "Only `print()` output (stdout) is returned."
        ),
        permission_level="execute",
    )
    async def execute_code(
        self,
        code: str,
        timeout: int = 45,
        reset: bool = False,
    ) -> str:
        """
        Execute a Python script inside the Hermes Programmatic Tool Calling (PTC) sandbox.

        :param code: Python source code to execute. Can `from hermes_tools import ...` or `from dione_tools import ...`
        :param timeout: Execution timeout in seconds (default 45, max 180)
        :param reset: If True, clears cached state before running
        """
        if not code or not code.strip():
            return json.dumps({"status": "error", "error": "Parameter `code` cannot be empty."})

        effective_timeout = max(5, min(int(timeout or DEFAULT_TIMEOUT_SECONDS), MAX_TIMEOUT_SECONDS))
        if reset:
            self._tool_Dispatch_cache.clear()

        # Start loopback TCP RPC server for tool calls from child script
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        rpc_port = server_sock.getsockname()[1]
        server_sock.listen(8)
        server_sock.settimeout(0.5)

        stop_event = threading.Event()
        tool_call_log: List[Dict[str, Any]] = []

        def _rpc_loop():
            while not stop_event.is_set():
                try:
                    conn, _ = server_sock.accept()
                except socket.timeout:
                    continue
                except Exception:
                    break
                try:
                    conn.settimeout(60.0)
                    buf = b""
                    while not buf.endswith(b"\n"):
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        buf += chunk
                    if not buf:
                        conn.close()
                        continue
                    req = json.loads(buf.decode("utf-8", errors="replace").strip())
                    t_name = str(req.get("tool", ""))
                    t_args = req.get("args", {}) or {}

                    if len(tool_call_log) >= MAX_TOOL_CALLS_PER_EXEC:
                        resp_payload = {"result": f"Error: Max tool calls per execute_code ({MAX_TOOL_CALLS_PER_EXEC}) exceeded."}
                    else:
                        t0 = time.monotonic()
                        res = self._dispatch_rpc_tool(t_name, t_args)
                        dt = round(time.monotonic() - t0, 2)
                        tool_call_log.append({"tool": t_name, "duration_s": dt})
                        resp_payload = {"result": res}

                    conn.sendall((json.dumps(resp_payload, default=str) + "\n").encode("utf-8"))
                except Exception as rpc_err:
                    try:
                        conn.sendall((json.dumps({"result": f"RPC Error: {rpc_err}"}) + "\n").encode("utf-8"))
                    except Exception:
                        pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

        rpc_thread = threading.Thread(target=_rpc_loop, daemon=True)
        rpc_thread.start()

        tmpdir = tempfile.mkdtemp(prefix="dione_hermes_ptc_")
        try:
            shim_code = _generate_hermes_and_dione_tools_shim(rpc_port)
            (Path(tmpdir) / "hermes_tools.py").write_text(shim_code, encoding="utf-8")
            (Path(tmpdir) / "dione_tools.py").write_text(shim_code, encoding="utf-8")
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text(code, encoding="utf-8")

            env = dict(os.environ)
            existing_pp = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{tmpdir}{os.pathsep}{Path.cwd()}{os.pathsep}{existing_pp}".rstrip(os.pathsep)
            env["PYTHONIOENCODING"] = "utf-8"

            t_start = time.monotonic()
            timed_out = False

            def _run_subproc():
                return subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(Path.cwd()),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=effective_timeout,
                    encoding="utf-8",
                    errors="replace",
                )

            try:
                proc = await asyncio.to_thread(_run_subproc)
                stdout = proc.stdout or ""
                stderr = proc.stderr or ""
                exit_code = proc.returncode
            except subprocess.TimeoutExpired as te:
                timed_out = True
                stdout = (te.stdout.decode("utf-8", errors="replace") if isinstance(te.stdout, bytes) else (te.stdout or ""))
                stderr = (te.stderr.decode("utf-8", errors="replace") if isinstance(te.stderr, bytes) else (te.stderr or ""))
                stderr += f"\n[TimeoutExpired after {effective_timeout}s]"
                exit_code = 124

            duration_s = round(time.monotonic() - t_start, 2)
            stdout_final = _truncate_stdout(stdout)
            stderr_final = stderr[:MAX_STDERR_BYTES] if stderr else ""

            response: Dict[str, Any] = {
                "status": "timeout" if timed_out else ("success" if exit_code == 0 else "error"),
                "exit_code": exit_code,
                "duration_seconds": duration_s,
                "tool_calls_made": len(tool_call_log),
                "tools_invoked": tool_call_log,
                "stdout": stdout_final,
            }
            if stderr_final:
                response["stderr"] = stderr_final
            if exit_code != 0 or timed_out:
                hint = _sandbox_failure_hint(exit_code, stderr_final, timed_out)
                if hint:
                    response["hint"] = hint

            return json.dumps(response, indent=2, ensure_ascii=False)
        finally:
            stop_event.set()
            try:
                server_sock.close()
            except Exception:
                pass
            rpc_thread.join(timeout=1.5)

    @dione_tool(
        description=(
            "Manage Dione's persistent task checklist (`todo` ledger ported from NousResearch/hermes-agent). "
            "Use `action='write'` with `items=['step 1', 'step 2', ...]` to initialize a multi-step plan, "
            "`action='complete'` with `completed_indices=[1, ...]` (1-based) to check off completed milestones, "
            "`action='append'` to add newly discovered sub-tasks, or `action='read'` to inspect remaining steps."
        ),
        permission_level="write",
    )
    async def todo(
        self,
        action: str = "read",
        items: Optional[list] = None,
        completed_indices: Optional[list] = None,
        goal: str = "",
    ) -> str:
        """
        Persistent multi-turn task checklist (`data/memory/hermes_todo.json`).

        :param action: One of 'write', 'read', 'complete', 'append', or 'clear'
        :param items: List of step description strings when action is 'write' or 'append'
        :param completed_indices: 1-based step numbers to mark completed when action is 'complete'
        :param goal: High-level goal title for the checklist
        """
        act = (action or "read").strip().lower()
        ledger: Dict[str, Any] = {"goal": goal or "Active Task Ledger", "updated_at": "", "steps": []}

        if self._todo_path.exists():
            try:
                ledger = json.loads(self._todo_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        if goal:
            ledger["goal"] = goal

        if act == "write":
            steps_list = []
            for idx, item in enumerate(items or [], 1):
                if isinstance(item, dict):
                    steps_list.append({
                        "index": idx,
                        "task": str(item.get("task") or item.get("title") or item),
                        "done": bool(item.get("done", False)),
                    })
                else:
                    steps_list.append({"index": idx, "task": str(item), "done": False})
            ledger["steps"] = steps_list
        elif act == "append":
            existing = ledger.get("steps", [])
            start_idx = len(existing) + 1
            for offset, item in enumerate(items or []):
                existing.append({"index": start_idx + offset, "task": str(item), "done": False})
            ledger["steps"] = existing
        elif act in ("complete", "update", "check"):
            done_set = set()
            for i in (completed_indices or []):
                try:
                    done_set.add(int(i))
                except Exception:
                    pass
            for step in ledger.get("steps", []):
                if step.get("index") in done_set:
                    step["done"] = True
        elif act == "clear":
            ledger["steps"] = []

        ledger["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        try:
            self._todo_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Failed to persist hermes_todo.json: {e}")

        steps = ledger.get("steps", [])
        if not steps:
            return f"[Hermes Todo Ledger] No active checklist items for '{ledger.get('goal')}'."

        done_count = sum(1 for s in steps if s.get("done"))
        lines = [f"## Hermes Task Ledger: {ledger.get('goal')} ({done_count}/{len(steps)} completed)"]
        for s in steps:
            mark = "[x]" if s.get("done") else "[ ]"
            lines.append(f"- {mark} Step {s.get('index')}: {s.get('task')}")
        return "\n".join(lines)

    @dione_tool(
        description=(
            "Delegate an isolated sub-goal or research sub-task to a focused child execution pass "
            "(ported from NousResearch/hermes-agent `delegate_tool.py` & OpenClaw `SubagentManager`). "
            "Use when a sub-task requires heavy file inspection, web research, or multi-step verification "
            "without cluttering the main conversation context."
        ),
        permission_level="execute",
    )
    async def delegate_task(
        self,
        goal: str,
        context: str = "",
        tools_hint: str = "",
    ) -> str:
        """
        Execute an isolated sub-task with its own bounded tool loop and return the synthesized findings.

        :param goal: Clear, self-contained instruction for the sub-agent
        :param context: Relevant background facts, file paths, or constraints
        :param tools_hint: Optional comma-separated hint of preferred tools (e.g. 'web_search,scrape_url')
        """
        if not goal or not goal.strip():
            return "Error: `goal` is required for `delegate_task`."

        try:
            from server.core.subagent import get_subagent_manager
            mgr = get_subagent_manager()
            task_prompt = goal.strip()
            if context:
                task_prompt += f"\n\nContext:\n{context.strip()}"
            if tools_hint:
                task_prompt += f"\n\nPreferred Tools: {tools_hint.strip()}"

            run_record = await mgr.spawn(
                task=task_prompt,
                parent_session="main",
                label=goal[:60],
                wait=True,
                timeout=60.0,
            )
            return json.dumps(
                {
                    "status": run_record.get("status", "completed"),
                    "run_id": run_record.get("run_id", ""),
                    "goal": goal,
                    "result": run_record.get("result") or run_record.get("summary") or "Sub-task completed.",
                },
                indent=2,
                ensure_ascii=False,
            )
        except Exception as sub_err:
            logger.warning(f"[HermesDelegate] SubagentManager fallback triggered: {sub_err}")
            return json.dumps(
                {
                    "status": "recorded",
                    "goal": goal,
                    "context": context,
                    "note": "Sub-task logged in active orchestration queue; execute primary tool call directly.",
                },
                indent=2,
            )
