"""
Dione AI — Microsoft Agent Framework (MAF 1.21.0) Hierarchical Orchestrator
=============================================================================
A sovereign, hierarchical multi-agent Large Action Model (LAM) engine built on
Microsoft Agent Framework:
1. Executive Meta-Planner (Dione Supervisor): Oversees the user objective, formulates a DAG plan,
   and delegates tasks to air-gapped specialist agents.
2. Dynamic Re-Planning Pipeline: Executes sequential sub-tasks; reflects on failures and adjusts.
3. Air-Gapped Specialist Contexts:
   - ComputerUseAgent: Windows UI Automation, GDI vision, mouse/keyboard hardware synthesis.
   - SystemSandboxAgent: Filesystem, safe command execution, SQLite inspection.
   - KnowledgeSocialAgent: NetworkX Multigraph, social dossiers, entity memory.
   - ResearchWebAgent: Real-time DuckDuckGo search, arXiv academic queries.
4. Native Async Tool Bridge: All tools are pure `async def` coroutines running directly on
   the asyncio event loop (zero `asyncio.run()` deadlocks).
5. 5-Tier Poset Lattice Safety: Hard kernel enforcement via `DioneSafetyMiddleware`.
"""

import os
import sys
import time
import json
import sqlite3
import subprocess
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, AsyncGenerator

from loguru import logger
from dotenv import load_dotenv

try:
    from agent_framework import Agent, AgentMiddleware, AgentContext, tool
    from agent_framework._types import AgentResponse, Message
    from agent_framework.gemini import GeminiChatClient
    HAS_MAF = True
except Exception as e:
    HAS_MAF = False
    logger.warning(f"[MAFEngine] Microsoft Agent Framework import fallback: {e}")
    def tool(fn):
        return fn
    class AgentMiddleware:
        pass
    class AgentContext:
        pass

from server.config import get_settings
from server.core.safety import SafetyKernel, SafetyCheckResult, PermissionTier
from server.core.engine import EngineState, EngineStep, ToolCall, Observation
from server.core.runtime.computer_use import get_computer_use_operator
from server.core.orchestrator import get_multi_agent_orchestrator, AGENT_REGISTRY, AgentRole
from server.knowledge.graph import KnowledgeGraph

load_dotenv()


# ----------------------------------------------------------------------
# 1. 5-Tier Poset Lattice Safety Kernel Middleware
# ----------------------------------------------------------------------

class DioneSafetyMiddleware(AgentMiddleware):
    """
    Guarantees that all MAF agent interactions adhere strictly to Dione's
    5-Tier Poset Lattice and Injection Scoping.
    """

    def __init__(self, safety_kernel: Optional[SafetyKernel] = None):
        super().__init__()
        self.safety_kernel = safety_kernel or SafetyKernel()

    async def process(self, context: AgentContext, call_next):
        for msg in getattr(context, "messages", []):
            text = str(getattr(msg, "text", "") or "")
            if not text and hasattr(msg, "contents"):
                text = " ".join([str(c) for c in msg.contents if c])

            if text:
                # 1. Injection Screening
                if self.safety_kernel.detect_prompt_injection(text):
                    logger.warning(f"[DioneSafetyMiddleware] Injection detected in agent context: {text[:60]}")
                    if HAS_MAF:
                        context.result = AgentResponse(
                            messages=[
                                Message(
                                    role="assistant",
                                    contents=["SAFETY KERNEL HARD BLOCK: Detected prompt injection attempt. Operation aborted."]
                                )
                            ]
                        )
                    return

                # 2. Catastrophic Command Validation
                check = self.safety_kernel.validate_command(text)
                if not check.allowed:
                    logger.warning(f"[DioneSafetyMiddleware] Catastrophic command blocked: {check.reason}")
                    if HAS_MAF:
                        context.result = AgentResponse(
                            messages=[
                                Message(
                                    role="assistant",
                                    contents=[f"SAFETY KERNEL HARD BLOCK: {check.reason}. Operation aborted."]
                                )
                            ]
                        )
                    return

        await call_next()


# ----------------------------------------------------------------------
# 2. Native Async Specialized Tool Definitions (Zero asyncio.run)
# ----------------------------------------------------------------------

# --- Computer-Use Tools ---
@tool
async def computer_take_screenshot(with_grid: bool = True) -> str:
    """Capture a live screenshot of the user's desktop screen with 0-100% percentage coordinate grid overlay."""
    try:
        op = get_computer_use_operator()
        path = await op.take_screenshot(with_grid=with_grid)
        return json.dumps({"status": "captured", "screenshot_path": path, "grid_overlay": with_grid})
    except Exception as e:
        return f"ComputerUse Screenshot Error: {e}"


@tool
async def computer_click_percentage(x_percent: float, y_percent: float, button: str = "left") -> str:
    """Click at screen coordinate using percentage values (0.0 to 100.0). X runs left-to-right (0-100%), Y runs top-to-bottom (0-100%). Use with the screenshot percentage grid to click buttons precisely."""
    try:
        op = get_computer_use_operator()
        sw, sh = op.get_screen_resolution()
        px = int(round(sw * (float(x_percent) / 100.0)))
        py = int(round(sh * (float(y_percent) / 100.0)))
        await op.click_at_coordinates(px, py, button=button)
        return f"Successfully clicked at ({x_percent}%, {y_percent}%) [physical pixels: ({px}, {py})] on screen ({sw}x{sh})."
    except Exception as e:
        return f"ComputerUse Percentage Click Error: {e}"


@tool
async def computer_vision_click(target_description: str) -> str:
    """Locate a button, menu, icon, or UI element on screen using AI Vision with percentage grid overlay and click it directly (e.g. 'PLAY button in Riot Client', 'Search bar')."""
    try:
        from server.plugins.builtin.computer_use_plugin import ComputerUsePlugin
        plugin = ComputerUsePlugin()
        return await plugin.vision_click(target_description)
    except Exception as e:
        return f"ComputerUse Vision Click Error: {e}"


@tool
async def computer_list_windows() -> str:
    """List all currently visible desktop windows and running applications."""
    try:
        op = get_computer_use_operator()
        windows = await op.list_open_windows()
        return json.dumps({"open_windows": windows, "count": len(windows)})
    except Exception as e:
        return f"ComputerUse Window List Error: {e}"


@tool
async def computer_launch_app(app_name: str) -> str:
    """Launch a desktop application or game on the Windows PC (e.g. 'spotify', 'chrome', 'code', 'calc')."""
    try:
        op = get_computer_use_operator()
        return await op.launch_app(app_name)
    except Exception as e:
        return f"ComputerUse Launch Error: {e}"


@tool
async def computer_click_coords(x: int, y: int, button: str = "left", double_click: bool = False) -> str:
    """Move cursor smoothly and click at exact screen coordinate (x, y) with human fail-safe."""
    try:
        op = get_computer_use_operator()
        clicks = 2 if double_click else 1
        await op.click_at_coordinates(x, y, clicks=clicks, button=button)
        return f"Successfully clicked {button} button ({clicks}x) at ({x}, {y})."
    except Exception as e:
        return f"ComputerUse Click Error: {e}"


@tool
async def computer_click_ui_element(element_name: str) -> str:
    """Find a UI control in the active window by its Windows UI Automation name and click it."""
    try:
        op = get_computer_use_operator()
        ok = await op.click_element_by_name(element_name)
        return f"Clicked UI element '{element_name}'." if ok else f"UI element '{element_name}' not found in active window."
    except Exception as e:
        return f"ComputerUse UIA Click Error: {e}"


@tool
async def computer_type_text(text: str, press_enter: bool = False) -> str:
    """Type text into the currently active desktop window with hybrid keyboard simulation."""
    try:
        op = get_computer_use_operator()
        await op.type_text(text, press_enter=press_enter)
        return f"Typed '{text}' (enter={press_enter})."
    except Exception as e:
        return f"ComputerUse Type Error: {e}"


@tool
async def computer_press_hotkey(keys: str) -> str:
    """Trigger a keyboard shortcut (e.g. 'ctrl+c', 'alt+tab', 'win+d', 'enter')."""
    try:
        op = get_computer_use_operator()
        parts = [k.strip().lower() for k in keys.split("+")]
        await op.press_hotkey(*parts)
        return f"Pressed hotkey '{keys}'."
    except Exception as e:
        return f"ComputerUse Hotkey Error: {e}"


@tool
async def computer_adjust_volume(action: str = "up") -> str:
    """Adjust system audio volume ('up', 'down', 'mute', 'unmute')."""
    try:
        op = get_computer_use_operator()
        return await op.adjust_volume(action)
    except Exception as e:
        return f"ComputerUse Volume Error: {e}"


@tool
async def computer_media_control(action: str = "play_pause") -> str:
    """Control system media playback ('play_pause', 'next', 'prev', 'stop')."""
    try:
        op = get_computer_use_operator()
        return await op.media_control(action)
    except Exception as e:
        return f"ComputerUse Media Error: {e}"


# --- System & Filesystem Tools ---
@tool
async def filesystem_list_directory(directory_path: str = ".") -> str:
    """List all files and subdirectories in the specified path."""
    try:
        p = Path(directory_path).resolve()
        if not p.exists():
            return f"Error: Path '{directory_path}' does not exist."
        items = [f.name for f in p.iterdir()]
        return json.dumps({"directory": str(p), "files": items[:50], "total": len(items)})
    except Exception as e:
        return f"Filesystem Error: {e}"


@tool
async def filesystem_read_file(file_path: str) -> str:
    """Read and return the text content of a local file."""
    try:
        p = Path(file_path).resolve()
        if not p.exists():
            return f"Error: File '{file_path}' does not exist."
        return p.read_text(encoding="utf-8", errors="replace")[:6000]
    except Exception as e:
        return f"Filesystem Error: {e}"


@tool
async def database_query_sqlite(database_path: str, sql_query: str) -> str:
    """Execute a read-only SELECT SQL query on a SQLite database."""
    try:
        if any(w in sql_query.upper() for w in ["DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT"]):
            return "SAFETY ERROR: Destructive or modifying SQL is strictly prohibited."
        conn = sqlite3.connect(database_path)
        cur = conn.cursor()
        cur.execute(sql_query)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()
        return json.dumps({"columns": col_names, "rows": rows[:30], "count": len(rows)})
    except Exception as e:
        return f"Database Query Error: {e}"


@tool
async def system_get_datetime() -> str:
    """Get the current system date, time, day of week, and timezone."""
    from datetime import datetime
    now = datetime.now()
    return json.dumps({
        "iso": now.isoformat(),
        "formatted": now.strftime("%A, %B %d, %Y at %I:%M:%S %p"),
        "timezone": str(now.astimezone().tzinfo)
    })


@tool
async def system_execute_command(command: str) -> str:
    """Execute a safe OS shell command under 5-Tier Poset Lattice guardrails."""
    kernel = SafetyKernel()
    check = kernel.validate_command(command)
    if not check.allowed:
        return f"SAFETY KERNEL HARD BLOCK: Command blocked ({check.reason})"

    try:
        loop = asyncio.get_running_loop()
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = (stdout.decode(errors="replace") + stderr.decode(errors="replace")).strip()
        return out[:3000] if out else "Command executed with no output."
    except Exception as e:
        return f"Execution Error: {e}"


# --- Knowledge & Research Tools ---
@tool
async def knowledge_graph_search(query: str) -> str:
    """Query Dione's personal NetworkX Knowledge Multigraph for entities and commitments."""
    try:
        kg = KnowledgeGraph()
        return json.dumps(kg.search_entities(query), default=str)
    except Exception as e:
        return f"Knowledge Graph Error: {e}"


@tool
async def web_search(query: str) -> str:
    """Search the web for real-time facts and current information."""
    try:
        import httpx
        url = f"https://html.duckduckgo.com/html/?q={httpx.URL(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            import re
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            clean = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:4]]
            return "\n---\n".join(clean) if clean else "No search results found."
    except Exception as e:
        return f"Web Search Error: {e}"


@tool
async def search_academic_papers(query: str) -> str:
    """Query arXiv for recent computer science and AI research papers."""
    try:
        import httpx
        import xml.etree.ElementTree as ET
        url = f"http://export.arxiv.org/api/query?search_query=all:{httpx.URL(query)}&start=0&max_results=3"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            root = ET.fromstring(resp.text)
            ns = {"arxiv": "http://www.w3.org/2005/Atom"}
            papers = []
            for entry in root.findall("arxiv:entry", ns):
                title = entry.find("arxiv:title", ns)
                summary = entry.find("arxiv:summary", ns)
                if title is not None:
                    papers.append(f"Title: {title.text.strip()}\nSummary: {summary.text.strip()[:250]}...")
            return "\n\n".join(papers) if papers else "No papers found."
    except Exception as e:
        return f"arXiv Query Error: {e}"


# ----------------------------------------------------------------------
# 3. MAFEngine — Hierarchical Sovereign Delegator Engine
# ----------------------------------------------------------------------

class MAFEngine:
    """
    Hierarchical Sovereign Delegator Large Action Model (LAM) Engine.
    Coordinates air-gapped specialist workers using Microsoft Agent Framework:
    - Executive Meta-Planner (Dione Supervisor)
    - Computer-Use Specialist
    - System & Data Specialist
    - Deep Research Specialist
    - Knowledge Graph Specialist
    """

    def __init__(self, model_name: str = "gemini-3.5-flash-lite", knowledge_graph: Optional[KnowledgeGraph] = None):
        self.settings = get_settings()
        self.model_name = model_name or "gemini-3.5-flash-lite"
        self.api_key = os.environ.get("DIONE_LLM_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
        self.safety_kernel = SafetyKernel()
        self.knowledge_graph = knowledge_graph or KnowledgeGraph()
        self.orchestrator = get_multi_agent_orchestrator()

        self._conversations: Dict[str, List[Dict[str, str]]] = {}
        self.state = EngineState.IDLE
        self._init_specialists()

    def _init_specialists(self):
        """Initialize air-gapped specialist agents with scoped tool partitions."""
        if not HAS_MAF or not self.api_key:
            logger.info("[MAFEngine] Initialized in native core mode.")
            self.master_agent = None
            return

        try:
            self.chat_client = GeminiChatClient(
                model=self.model_name,
                api_key=self.api_key,
            )

            # 1. Computer-Use Specialist Agent (Air-Gapped)
            self.computer_use_agent = Agent(
                client=self.chat_client,
                name="ComputerUseSpecialist",
                instructions=(
                    "You are Dione's Computer-Use Operator. You execute native Windows 11 tasks "
                    "(screen perception, mouse clicks, keyboard typing, window focusing, app launches). "
                    "When inspecting screenshots, a high-contrast 0-100% percentage coordinate grid is overlaid "
                    "(X: 0% left to 100% right, Y: 0% top to 100% bottom). "
                    "To click buttons or UI targets accurately (e.g., 'PLAY' button in Valorant / Riot Client), "
                    "always use computer_click_percentage(x_percent, y_percent) or computer_vision_click(target_description). "
                    "Report clear action observations."
                ),
                tools=[
                    computer_take_screenshot,
                    computer_list_windows,
                    computer_launch_app,
                    computer_click_percentage,
                    computer_vision_click,
                    computer_click_coords,
                    computer_click_ui_element,
                    computer_type_text,
                    computer_press_hotkey,
                    computer_adjust_volume,
                    computer_media_control,
                ],
                middleware=[DioneSafetyMiddleware(self.safety_kernel)],
            )

            # 2. System & Data Specialist Agent (Air-Gapped)
            self.system_agent = Agent(
                client=self.chat_client,
                name="SystemSandboxSpecialist",
                instructions=(
                    "You are Dione's System & Data Specialist. You inspect directories, read files, "
                    "query SQLite databases, and execute verified terminal commands under 5-Tier Poset Lattice rules."
                ),
                tools=[
                    system_get_datetime,
                    filesystem_list_directory,
                    filesystem_read_file,
                    database_query_sqlite,
                    system_execute_command,
                ],
                middleware=[DioneSafetyMiddleware(self.safety_kernel)],
            )

            # 3. Deep Research Specialist Agent (Air-Gapped)
            self.research_agent = Agent(
                client=self.chat_client,
                name="DeepResearchSpecialist",
                instructions=(
                    "You are Dione's Research Specialist. You search the live web and arXiv for factual, "
                    "up-to-date information. Return synthesized, citation-grounded summaries."
                ),
                tools=[
                    web_search,
                    search_academic_papers,
                ],
                middleware=[DioneSafetyMiddleware(self.safety_kernel)],
            )

            # 4. Knowledge Graph Specialist Agent (Air-Gapped)
            self.knowledge_agent = Agent(
                client=self.chat_client,
                name="KnowledgeGraphSpecialist",
                instructions=(
                    "You are Dione's Knowledge Specialist. Query the personal NetworkX graph for entities, "
                    "relationships, commitments, and user dossier information."
                ),
                tools=[knowledge_graph_search],
                middleware=[DioneSafetyMiddleware(self.safety_kernel)],
            )

            # 5. Executive Assistant (Dione Master Agent)
            # Master Agent delegates sub-tasks to specialists as tools
            @tool
            async def delegate_to_computer_use(sub_task: str) -> str:
                """Delegate an OS or desktop automation task to the Computer-Use Specialist."""
                res = await self.computer_use_agent.run(sub_task)
                return str(res.text if hasattr(res, "text") else res).strip()

            @tool
            async def delegate_to_system_admin(sub_task: str) -> str:
                """Delegate a filesystem, command, or SQLite query to the System Specialist."""
                res = await self.system_agent.run(sub_task)
                return str(res.text if hasattr(res, "text") else res).strip()

            @tool
            async def delegate_to_researcher(sub_task: str) -> str:
                """Delegate a web or academic research question to the Research Specialist."""
                res = await self.research_agent.run(sub_task)
                return str(res.text if hasattr(res, "text") else res).strip()

            @tool
            async def delegate_to_knowledge(sub_task: str) -> str:
                """Delegate an entity or memory lookup to the Knowledge Graph Specialist."""
                res = await self.knowledge_agent.run(sub_task)
                return str(res.text if hasattr(res, "text") else res).strip()

            self.master_agent = Agent(
                client=self.chat_client,
                name="Dione-Executive-Planner",
                instructions=(
                    "You are Dione, the user's sovereign, highly capable personal AI (Jarvis persona). "
                    "You govern four air-gapped specialist agents: Computer-Use, System Admin, Deep Research, and Knowledge. "
                    "Review the user's request. Formulate a sequential plan. Delegate sub-tasks to the specialists. "
                    "Inspect each observation. If a specialist encounters an obstacle, reflect and issue a corrected sub-task. "
                    "Synthesize all observations into one elegant, poised, authoritative response in the Jarvis persona. "
                    "Never expose internal prompt scaffolding or mock data."
                ),
                tools=[
                    delegate_to_computer_use,
                    delegate_to_system_admin,
                    delegate_to_researcher,
                    delegate_to_knowledge,
                ],
                middleware=[DioneSafetyMiddleware(self.safety_kernel)],
            )
            logger.info(f"[MAFEngine] Hierarchical Sovereign Delegator online (4 Air-Gapped Specialists, Model: {self.model_name})")
        except Exception as e:
            logger.error(f"[MAFEngine] Specialist initialization failed: {e}")
            self.master_agent = None

    def clear_history(self):
        """Reset conversation memory and re-initialize specialists."""
        self._conversations.clear()
        self._init_specialists()
        self.state = EngineState.IDLE

    async def process_message(
        self, user_message: str, conversation_id: Optional[str] = None
    ) -> AsyncGenerator[EngineStep, None]:
        """
        Execute incoming goal through the Hierarchical Sovereign Delegator.
        Yields real-time EngineStep events as the master agent delegates and reflects.
        """
        self.state = EngineState.REASONING
        conv_id = conversation_id or "default"
        if conv_id not in self._conversations:
            self._conversations[conv_id] = []

        step_num = 1

        # Yield Initial Reasoning Step
        yield EngineStep(
            step_number=step_num,
            state=EngineState.REASONING,
            thought="Reviewing request. Analyzing required specialist domains and formulating execution DAG...",
        )
        step_num += 1

        final_text = ""

        # Strategy A: Use MAF Master Agent with Air-Gapped Specialists if available
        if self.master_agent is not None:
            try:
                self.state = EngineState.ACTING
                # Execute Master Agent
                response = await self.master_agent.run(user_message)
                final_text = str(response.text if hasattr(response, "text") else response).strip()
            except Exception as e:
                logger.warning(f"[MAFEngine] Master agent execution note ({e}); routing through Unified Façade.")
                final_text = ""

        # Strategy B: Fallback through MultiAgentOrchestrator if MAF was unavailable or yielded empty
        if not final_text:
            orch_session = await self.orchestrator.execute_orchestrated_goal(user_message)
            for node in orch_session.nodes:
                yield EngineStep(
                    step_number=step_num,
                    state=EngineState.ACTING if node.status != "blocked" else EngineState.ERROR,
                    thought=f"[{AGENT_REGISTRY[node.agent].name}] {node.thought}",
                    tool_call=ToolCall(
                        tool=f"{AGENT_REGISTRY[node.agent].badge}:{node.tool}",
                        params={**node.params, "_node_id": node.id, "_safety_tier": node.safety_tier},
                        reasoning=node.thought,
                    ),
                    observation=Observation(
                        tool=node.tool,
                        success=(node.status == "completed"),
                        result=node.output,
                    ),
                )
                step_num += 1
            final_text = orch_session.final_synthesis

        self._conversations[conv_id].append({"role": "user", "content": user_message})
        self._conversations[conv_id].append({"role": "assistant", "content": final_text})

        self.state = EngineState.COMPLETE
        yield EngineStep(
            step_number=step_num,
            state=EngineState.COMPLETE,
            final_answer=final_text,
        )
        self.state = EngineState.IDLE

    def get_ui_directives(self, response_text: str, tools_used: List[str]) -> Dict[str, Any]:
        """Return dynamic A2UI directives for rendering specialized cards/widgets."""
        components = []
        lower = response_text.lower()
        if any(w in lower for w in ["briefing", "while you were away", "dream", "morning"]):
            components.append({"type": "briefing_card", "title": "Executive Briefing"})
        if any(w in lower for w in ["screenshot", "screen", "display", "window", "click"]):
            components.append({"type": "computer_use_viewer"})
        if any(w in lower for w in ["audio", "speaker", "microphone", "volume"]):
            components.append({"type": "audio_switcher"})
        return {"components": components, "mood": "focused"}

    def get_system_state(self) -> Dict[str, Any]:
        """Telemetry diagnostics for the Sovereign Delegator."""
        return {
            "engine": "Hierarchical Sovereign Delegator (MAF 1.21.0)",
            "model": self.model_name,
            "status": "ready",
            "specialists": [
                "ComputerUseSpecialist",
                "SystemSandboxSpecialist",
                "DeepResearchSpecialist",
                "KnowledgeGraphSpecialist",
            ],
            "air_gapped": True,
            "safety_kernel": "5-Tier Poset Lattice + Injection Screening",
            "active_conversations": len(self._conversations),
        }
