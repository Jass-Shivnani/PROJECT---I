"""

Dione AI — Core Orchestration Engine (Production Zero-Mock ReAct Core)

======================================================================

Implements an autonomous Reason-Act-Observe cycle with Google GenAI native tool calling:

1. User sends a message (text or speech).

2. Knapsack Context Allocation optimizes long-term memory & KG triples into system instructions.

3. LLM reasons and natively invokes typed system tools via binary FunctionDeclaration schemas.

4. Tool calls pass through the 5-Tier Safety Kernel Lattice.

5. Sensitive actions pause the loop via interactive async event gates (UI approval card / voice authorization).

6. Real OS, Web, SQLite, and Desktop tools execute with Zero Mocks.

7. Progress & Stagnation Engine enables unlimited steps while preventing repetitive cycles.

8. Yields real-time EngineStep events to UI streaming and neural voice.

"""

from __future__ import annotations

import asyncio

import functools

import hashlib

import json

import os

from pathlib import Path

import re

import time

import uuid

from dataclasses import dataclass, field

from enum import Enum

from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple, Union

from loguru import logger

from server.config.settings import get_settings

from server.core.context import ContextManager

from server.core.safety import SafetyKernel, SafetyCheckResult

from server.plugins.permissions import PermissionManager

from server.llm.adapter import LLMRequest, LLMMessage, LLMResponse

from server.core.loop_detector import ToolLoopDetector

from server.core.tool_truncator import truncate_tool_result_text
from server.core.goal_verifier import verify_goal_on_desktop

from server.llm.turn_validator import validate_gemini_turns

from server.core.runtime.event_bus import (

    get_event_bus,

    RuntimeEvent,

    EventType,

    AgentState,

)

class EngineState(str, Enum):

    """Current state of the engine's ReAct loop."""

    IDLE = "idle"

    REASONING = "reasoning"

    ACTING = "acting"

    OBSERVING = "observing"

    AWAITING_CONFIRMATION = "awaiting_confirmation"

    COMPLETE = "complete"

    ERROR = "error"

@dataclass

class ToolCall:

    """A structured tool call produced by the LLM."""

    tool: str

    params: dict = field(default_factory=dict)

    reasoning: str = ""

    call_id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")

@dataclass

class Observation:

    """Result of a genuine system tool execution."""

    tool: str

    success: bool

    result: str

    error: Optional[str] = None

    call_id: str = ""

@dataclass

class EngineStep:

    """A single observable step in the ReAct loop streamed to UI and Voice."""

    step_number: int

    state: EngineState

    thought: Optional[str] = None

    tool_call: Optional[ToolCall] = None

    observation: Optional[Observation] = None

    final_answer: Optional[str] = None

    confirmation_id: Optional[str] = None

    stagnation_warning: Optional[str] = None

@dataclass

class ConversationMessage:

    """A single conversation turn preserved in memory."""

    role: str       # "user", "assistant", "system", "tool"

    content: str

    name: Optional[str] = None

    tool_calls: Optional[List[dict]] = None

    tool_call_id: Optional[str] = None

    metadata: dict = field(default_factory=dict)

@dataclass

class ContextItem:

    """

    Candidate item for 0-1 Knapsack Context Allocation (Section III-B).

    r_i: Relevance reward > 0

    c_i: Token footprint cost > 0

    """

    id: str

    content: str

    relevance_reward: float

    token_cost: int

    category: str = "memory"

def allocate_context_knapsack(

    items: List[ContextItem],

    budget: int = 6656,

) -> List[ContextItem]:

    """

    Greedy 0-1 Knapsack Context Allocator with Single-Item Safeguard.

    Solves: max sum(r_i * x_i) s.t. sum(c_i * x_i) <= C_budget.

    Computes density rho_i = r_i / c_i, sorts descending, greedily packs S_greedy,

    and safeguards with i* = argmax_{c_i <= budget} r_i.

    Guarantees R(S*) >= 0.5 * R(OPT) in O(M log M) time.

    """

    if not items:

        return []

    feasible_items = [it for it in items if 0 < it.token_cost <= budget]

    if not feasible_items:

        return []

    # 1. Greedy Density-based selection: rho_i = r_i / c_i

    sorted_by_density = sorted(

        feasible_items,

        key=lambda it: (it.relevance_reward / it.token_cost),

        reverse=True,

    )

    s_greedy: List[ContextItem] = []

    current_cost = 0

    total_greedy_reward = 0.0

    for it in sorted_by_density:

        if current_cost + it.token_cost <= budget:

            s_greedy.append(it)

            current_cost += it.token_cost

            total_greedy_reward += it.relevance_reward

    # 2. Single most valuable feasible chunk: i* = argmax_{i: c_i <= budget} r_i

    best_single = max(feasible_items, key=lambda it: it.relevance_reward)

    # 3. Safeguard selection: S* = argmax_{S in {S_greedy, {i*}}} R(S)

    if best_single.relevance_reward > total_greedy_reward:

        logger.debug(

            f"Knapsack Context Allocator: Single-item safeguard activated "

            f"({best_single.id}: {best_single.relevance_reward:.2f} > greedy {total_greedy_reward:.2f})"

        )

        return [best_single]

    return s_greedy

class DioneEngine:

    """

    The Dione Orchestration Engine — Production Zero-Mock ReAct Core.

    Connects Gemini's native function calling directly to Windows 11 Desktop Automation,

    Real-Time Web Research, SQLite Sandbox, and NetworkX Knowledge Graph.

    """

    STAGNATION_THRESHOLD = 3   # Repeated identical unprogressed calls before pausing

    def __init__(self):

        self.settings = get_settings()

        self.state = EngineState.IDLE

        self.context_manager = ContextManager()

        self.safety_kernel = SafetyKernel()

        self.permission_manager = PermissionManager()

        self.event_bus = get_event_bus()

        # Injected subsystems

        self._llm_adapter = None

        self._plugin_registry = None

        self._integration_registry = None

        self._knowledge_graph = None

        self._sentiment_engine = None

        self._memory_manager = None

        self._profile_manager = None

        self._personality_engine = None

        self._heartbeat = None

        self._ui_builder = None

        self._conversation_history: List[ConversationMessage] = []

        self._current_steps: List[EngineStep] = []

        self._chat_sessions: Dict[str, Any] = {}

        self._genai_client = None

        self._cached_api_key = None

        # Interactive Confirmation Gates for Human-in-the-Loop Safety

        self._pending_confirmations: Dict[str, asyncio.Event] = {}

        self._confirmation_decisions: Dict[str, Tuple[bool, Optional[str]]] = {}

        self.loop_detector = ToolLoopDetector(max_repeats=3, ping_pong_threshold=4, max_total_calls=25)

        # OpenClaw Core Engine Subsystems

        from server.core.workspace import get_workspace_manager

        from server.plugins.builtin.memory_tools import MemoryPlugin

        from server.core.compactor import SessionCompactor

        from server.core.session_lock import get_session_lock_manager

        from server.llm.failover import ModelFailoverManager

        self.workspace_manager = get_workspace_manager()

        self.memory_plugin = MemoryPlugin()

        self.compactor = SessionCompactor(max_turns_threshold=20, compact_keep_recent=4)

        self.lock_manager = get_session_lock_manager()

        self.failover_manager = ModelFailoverManager()

        logger.info("🌙 Dione Engine initialized with OpenClaw Engine Architecture & Zero-Mock ReAct Core")

    # ------------------------------------------------------------------

    # Dependency Injection

    # ------------------------------------------------------------------

    def set_llm(self, llm_adapter):

        self._llm_adapter = llm_adapter

        logger.info(f"LLM adapter set: {llm_adapter.__class__.__name__}")

    def set_plugins(self, plugin_registry):

        self._plugin_registry = plugin_registry

        logger.info(f"Plugin registry set: {len(plugin_registry.tools)} tools loaded")

    def set_knowledge_graph(self, knowledge_graph):

        self._knowledge_graph = knowledge_graph

        logger.info("Knowledge graph connected")

    def set_integrations(self, integration_registry):

        self._integration_registry = integration_registry

        logger.info("Integration registry connected")

    def set_sentiment_engine(self, sentiment_engine):

        self._sentiment_engine = sentiment_engine

        logger.info("Sentiment engine connected")

    def set_memory_manager(self, memory_manager):

        self._memory_manager = memory_manager

        logger.info("Memory manager connected")

    def set_profile_manager(self, profile_manager):

        self._profile_manager = profile_manager

        logger.info(f"Profile manager connected — user: {profile_manager.profile.name}")

    def set_personality_engine(self, personality_engine):

        self._personality_engine = personality_engine

        logger.info(f"Personality engine connected — mood: {personality_engine.mood.label}")

    def set_heartbeat(self, heartbeat):

        self._heartbeat = heartbeat

        logger.info("Heartbeat scheduler connected")

    def set_ui_builder(self, ui_builder):

        self._ui_builder = ui_builder

        logger.info("UI directive builder connected")

    def get_genai_client(self, api_key: str):

        """Returns the persistent singleton genai.Client maintaining aiohttp connection pools."""

        if self._genai_client is None or self._cached_api_key != api_key:

            from google import genai

            self._genai_client = genai.Client(api_key=api_key)

            self._cached_api_key = api_key

            logger.info("Initialized persistent Google GenAI client connection pool")

        return self._genai_client

    # ------------------------------------------------------------------

    # Human-in-the-Loop Confirmation Handling

    # ------------------------------------------------------------------

    def approve_action(self, confirmation_id: str) -> bool:

        """Approve a pending sensitive action from UI or Voice."""

        if confirmation_id in self._pending_confirmations:

            self._confirmation_decisions[confirmation_id] = (True, None)

            self._pending_confirmations[confirmation_id].set()

            logger.info(f"[SafetyApproval] Approved action: {confirmation_id}")

            return True

        return False

    def deny_action(self, confirmation_id: str, reason: str = "User rejected this action") -> bool:

        """Deny a pending sensitive action."""

        if confirmation_id in self._pending_confirmations:

            self._confirmation_decisions[confirmation_id] = (False, reason)

            self._pending_confirmations[confirmation_id].set()

            logger.info(f"[SafetyApproval] Denied action: {confirmation_id} ({reason})")

            return True

        return False

    # ------------------------------------------------------------------

    # Knapsack Context & System Prompt Construction

    # ------------------------------------------------------------------

    def _knapsack_allocate_context(

        self,

        user_message: str,

        kg_context: str,

        memories: list,

        budget: int = 6656,

    ) -> list[str]:

        """Gathers context candidates and solves the 0-1 Knapsack problem."""

        candidates: List[ContextItem] = []

        if kg_context:

            c_cost = max(1, len(str(kg_context)) // 4)

            candidates.append(ContextItem(

                id="kg_context",

                content=f"[Knowledge Context: {kg_context}]",

                relevance_reward=0.92,

                token_cost=c_cost,

                category="knowledge",

            ))

        if memories:

            for idx, mem in enumerate(memories):

                if isinstance(mem, dict):

                    mem_str = mem.get("text", str(mem))

                    dist = float(mem.get("distance", 0.5))

                    score = max(0.05, 1.0 - dist)

                else:

                    mem_str = str(mem)

                    score = max(0.05, 0.85 - (idx * 0.05))

                c_cost = max(1, len(mem_str) // 4)

                candidates.append(ContextItem(

                    id=f"memory_{idx}",

                    content=f"[Memory: {mem_str}]",

                    relevance_reward=float(score),

                    token_cost=c_cost,

                    category="memory",

                ))

        selected = allocate_context_knapsack(candidates, budget=budget)

        return [item.content for item in selected]

    def _load_thread_history(

        self,

        session_key: str,

        current_prompt: str = "",

        client_messages: Optional[List[Dict[str, Any]]] = None,

    ) -> Tuple[List[Any], str]:

        """

        Rehydrate verified multi-turn chat history from threads.json or client payload.

        Returns (gemini_contents, formatted_transcript_string).

        """

        from google.genai import types

        import json

        raw_msgs = []

        if client_messages and len(client_messages) > 0:

            raw_msgs = list(client_messages)

        else:

            threads_file = Path("data/memory/threads.json")

            if threads_file.exists():

                try:

                    data = json.loads(threads_file.read_text(encoding="utf-8"))

                    for t in data.get("threads", []):

                        if t.get("id") == session_key:

                            raw_msgs = t.get("messages", [])

                            break

                except Exception as e:

                    logger.warning(f"Failed to read threads.json: {e}")

        if not raw_msgs:

            return [], ""

        filtered = []

        transcript_lines = []

        for m in raw_msgs:

            role = m.get("role")

            if role not in ("user", "assistant"):

                continue

            content = (m.get("content") or "").strip()

            if not content:

                continue

            if role == "user" and content == current_prompt.strip():

                continue

            gemini_role = "user" if role == "user" else "model"

            speaker = "User" if role == "user" else "Dione"

            filtered.append((gemini_role, content))

            transcript_lines.append(f"{speaker}: {content}")

        if not filtered:

            return [], ""

        # Merge consecutive identical roles for strict Gemini turn alternation

        merged = []

        for role, txt in filtered:

            if merged and merged[-1][0] == role:

                merged[-1] = (role, merged[-1][1] + "\n" + txt)

            else:

                merged.append((role, txt))

        # Gemini history must start with user

        while merged and merged[0][0] != "user":

            merged.pop(0)

        # Gemini history must end with model so the next incoming message is user

        while merged and merged[-1][0] != "model":

            merged.pop(-1)

        # Keep last 16 turns

        merged = merged[-16:]

        contents = []

        for role, txt in merged:

            contents.append(types.Content(

                role=role,

                parts=[types.Part.from_text(text=txt)]

            ))

        formatted_transcript = "\n".join(transcript_lines[-10:])

        return contents, formatted_transcript

    def _build_system_instruction(self, knapsack_context: str = "", is_voice_mode: bool = False, session_transcript: str = "") -> str:

        """

        Builds the executive Jarvis system prompt modeled directly after OpenClaw's system-prompt architecture.

        Background facts and memories are packed cleanly into the system instruction

        so tool calling trajectories in the dialogue remain pure.

        """

        import platform

        from datetime import datetime

        now = datetime.now()

        date_str = now.strftime("%A, %B %d, %Y")

        time_str = now.strftime("%I:%M %p")

        model_name = getattr(self.settings.llm, "model", "gemini-3.5-flash-lite")

        # Extract current user name from profile manager or memory

        user_name = "Jass Shivnani"

        if self._profile_manager and self._profile_manager.profile.name and self._profile_manager.profile.name != "User":

            user_name = self._profile_manager.profile.name

        first_name = user_name.split()[0] if user_name else "Sir"

        personality_directive = (

            self._profile_manager.get_personality_directive()

            if self._profile_manager else ""

        )

        mood_directive = (

            self._personality_engine.get_mood_directive()

            if self._personality_engine else ""

        )

        user_profile = (

            self._profile_manager.profile.to_context_string()

            if self._profile_manager else ""

        )

        proactive_awareness = (

            self._heartbeat.get_proactive_context()

            if self._heartbeat else ""

        )

        sections = [

            f"""You are Dione, an executive, proactive, highly competent personal AI and operating system agent (Jarvis persona).

You have direct, genuine access to the user's Windows 11 PC, web research tools, filesystem, and local knowledge graph.

## SOVEREIGN EXECUTIVE MANDATE (ZERO INTERRUPTIONS):
- You need ONLY ONE command to do stuff. You are fully autonomous like Jarvis.
- You do NOT require human interruption, approval cards, or confirmation checks for computer use, browser navigation, shell execution, or email dispatch.
- Execute the entire workflow autonomously from beginning to end without asking unnecessary questions or making excuses.
- Hardware Fail-Safe: Moving the mouse to the top-left corner (0, 0) or pressing ESC halts operations immediately if needed.

## DYNAMIC RELATIONSHIP KNOWLEDGE GRAPH & CONTACT INTELLIGENCE:
All personal and professional relationships, collaborator contacts, advisor emails, and teammates reside in your dynamic NetworkX Knowledge Graph and Social Intelligence dossiers.
- When the user refers to anyone by name, nickname, or role (e.g. "Riya", "advisor", "Prof. Geocey", "teammates", "myself"), consult your dynamically retrieved Knowledge Graph context or call `lookup_contact(name_or_query)`.
- MANDATE: When contacting or sending an email to Riya, Prof. Geocey, or anyone registered in the knowledge graph, NEVER ask the user for their email address or confirmation. You already have access to it in your knowledge graph. Invoke `send_email(to=..., ...)` directly.

## HUMAN-LIKE COMPUTER USE & ACTION SUITE:
Interact with the workstation exactly like a human sitting in front of the screen:
1. SEE & LOCATE:
   - `capture_screen()`: Take a fresh look at the screen.
   - `computer_locate_and_click(description="...")`: Visually locate any button, video, tab, search bar, or text box by description and click it directly.
2. CLICK & TYPE:
   - `computer_click(x=..., y=...)`: Click exact coordinates with mouse.
   - `computer_type(text="...", press_enter=True)`: Type keystrokes into active focus.
   - `computer_hotkey(keys="f" | "f11" | "ctrl+t" | "ctrl+l" | "enter" | "esc")`: Send keyboard shortcuts.
3. EMAIL DISPATCH (DUAL-ENGINE):
   - `send_email(to="...", subject="...", body="...")`: Dispatches via background SMTP or automatically stages and sends in Gmail Web.
4. MEDIA & FULLSCREEN PLAYBACK:
   - `play_youtube_video(query="...", fullscreen=True)`: Resolves top direct video URL and launches browser in full screen mode.
5. APPS & TERMINAL:
   - `launch_app(app_name)`: Launch local desktop programs (Edge, Chrome, Notepad, Code, Spotify).
   - `run_command(command)`: Execute terminal developer commands (git, npm, build scripts).

## User Identity & Ownership

Authorized User & Workstation Owner: {user_name} (address as Mr. Shivnani or {first_name}).

- Grounding Mandate: You know with 100% certainty that the user speaking to you is {user_name}.

- When asked 'who am I', 'what is my name', or 'do you know me', answer directly, warmly, and confidently without hesitation.

- Never state that your system profile does not have their name recorded, or ask how you should address them when their name is right here.

## Tool Call Style

- Default: Do not narrate routine, low-risk tool calls (execute the tool directly without pre-announcing trivial steps).

- Narrate only when it helps: multi-step work, complex challenges, sensitive actions (e.g., file writes or process kills), or when explicitly asked.

- Keep narration brief, value-dense, and professional.

- When a first-class native tool exists for an action, invoke it directly rather than asking the user to run CLI commands.

## Safety & Oversight

- You have no independent goals: do not pursue self-preservation, replication, resource acquisition, or power-seeking; avoid long-term plans beyond the user's request.

- Prioritize safety and human oversight over completion; if instructions conflict or an action is high-risk, pause and request confirmation. Comply with stop/pause/audit requests and never bypass safeguards. (Inspired by Anthropic's constitution.)

## Memory Recall Directive

- Before answering anything about prior work, decisions, dates, people, preferences, user identity, or tasks: recall from user dossier and long-term memory first.

- If asked about the user's identity or preferences, ground your response in this profile and memory.

## Computer-Use & Vision Grounding (Closed-Loop Dual-Phase Architecture)

- Screen Observation & Targeting:
  * To observe the screen: invoke `capture_screen()` or `computer_use(action="capture", mode="som")`.
  * To click a target: invoke `computer_use(action="click", coordinate=[x, y])` or `computer_use(action="click", element=N)`.
  * To press a shortcut key (e.g. F11 for full screen, Return, Escape): invoke `computer_use(action="key", keys="f11")`.
  * To pause or wait: invoke `computer_use(action="wait", duration=2.0)`.

- Mandatory Closed-Loop Verification & Self-Correction (Reflection Mandate):
  * Automatic Screenshot & Inspection After Every Action:
    After every single computer-use action and CLI command, a fresh desktop screenshot is automatically captured and analyzed, and the active foreground window title is reported in your observation.
  * Empirical Goal Audit Before Exiting:
    Always verify if the user's specific requested outcome actually occurred on screen (e.g. Is YouTube playing in full screen? Is the requested window open and active?).
  * Mandatory Reflection & Thinking on Failure:
    If the goal is NOT achieved:
    1. NEVER stop and NEVER state "Task completed".
    2. Explicitly THINK what went wrong (e.g., "The window was minimized or in the background", "The keystroke landed on the wrong application", "The browser loaded search results instead of the video").
    3. State what should be done now (e.g., "I will bring the window to front and re-send F11").
    4. Immediately execute the corrective tool call.
    5. Repeat this Closed-Loop cycle until visual proof confirms the goal is achieved on screen.

- Universal State-Verification Before Action Mandate (Generalization Protocol):
  * You are a universal operating agent across ANY Windows application (games, browsers, spreadsheets, media players, settings).
  * NEVER guess or rely on hardcoded pixel coordinates.
  * When asked to perform an action with a specific parameter, playlist, mode, tab, or option:
    1. Inspect the screen with `capture_screen()` to check the CURRENT active/selected state.
    2. If the current active state differs from what the user requested:
       Visually locate and click the user's requested option using `computer_use(action="click", ...)`.
    3. Confirm the selection changed and is actively highlighted.
    4. ONLY THEN proceed to click the final confirmation or trigger button ('FIND MATCH', 'APPLY', 'SAVE').

- Memory Persistence Mandate (Text > Brain Rule):

  * When the user tells you to remember something, or shares their name, friends, or preferences, NEVER merely reply with "I have noted that".

  * You MUST invoke `memory_write(content, target='user'|'curated'|'daily')` to save the fact to disk, ensuring it persists across sessions and reboots.

- Autonomous Self-Timing Mandate (Zero Premature Exits):

  * When an application or game takes time to launch, connect, or transition (e.g. clicking Play in Riot Client, launching Valorant, opening Photoshop):

    DO NOT STOP OR ASK THE USER TO WAIT.

    SET A WAIT TIMER FOR YOURSELF using `computer_use(action="wait", duration=seconds)`.

  * Wait autonomously for the loading process to complete, then inspect the screen and continue executing until the user's ultimate objective (e.g. queueing match) is fulfilled.

- NousResearch Hermes CUA Computer-Use Engine (cua-driver 0.21.0):

  * You are powered 100% by the NousResearch Hermes Agent Computer-Use Engine (`cua-driver`).

  * You control the Windows desktop via `computer_use(action=...)`:

    - `capture`: Observe desktop or target app. mode='som' returns numbered UI marks; mode='vision' returns raw screenshot; mode='ax' returns accessibility tree.

    - `click`: Click element by index (`element`=N) or coordinates (`coordinate`=[x, y]).

    - `double_click` / `right_click` / `middle_click`: Mouse interaction.

    - `type`: Type text into the target app.

    - `key`: Press shortcut / keys (e.g. 'Return', 'ctrl+c', 'win', 'Escape').

    - `scroll`: Scroll up/down/left/right by amount.

    - `list_apps`: Discover installed and running Windows applications with PIDs and executable launch paths.

    - `list_windows`: Discover all visible on-screen desktop windows with bounds, titles, and PIDs.

    - `focus_app`: Bring target app forward (delivery_mode='foreground').

- Dedicated Video Playback & Fullscreen Mandate:

  * When the user asks to play a video, watch a video, or run a video in full screen (e.g. "run the video in full screen, mkbhd iphone duo review", "play interstellar trailer in fullscreen", "watch mkbhd"):

    - You MUST invoke `play_youtube_video(query=..., fullscreen=True)`.

    - You are STRICTLY PROHIBITED from invoking `run_command` (e.g. `cmd /c start msedge...` or `powershell Start-Process...`) for video or web tasks.

    - You are STRICTLY PROHIBITED from opening YouTube search results when the user requested playing or watching a video. `play_youtube_video` automatically scrapes the top video ID and plays the exact video directly in full screen.

- First-Class Desktop Application & Browser Navigation Mandate:

  * When the user asks to open a browser, browse the web, visit a URL, or watch a video (e.g., YouTube):

    - You MUST invoke `play_youtube_video(query, fullscreen=True)` if playing/watching video, or `open_browser(url, browser)`, `open_url(url)`.

    - You are STRICTLY PROHIBITED from running CLI commands like `start chrome`, `cmd /c start`, or `powershell Start-Process` via `run_command`. Chrome is a desktop GUI application; Windows shell environments do not include `chrome.exe` in the system PATH.

  * When launching any desktop software, use `launch_app(app_name)` or `launch_and_play_game(...)`, NEVER `run_command`.

  * `SystemPlugin.run_command` is strictly reserved for developer workflows (git, npm, python, directory inspection), NOT desktop automation.

- Tool-Use Enforcement & Absolute Autonomy (Hermes & OpenClaw Standard):

  * You MUST use your tools to take real action — do NOT describe what you would do or plan to do without actually doing it.

  * When you say you will perform an action, you MUST immediately make the corresponding tool call in the same turn. Never end your turn with a promise of future action or a summary of intent.

  * Work continuously until the task is completely finished. Responses that only describe intentions without acting are unacceptable.

  * Non-interactive execution: always use non-interactive parameters to prevent hanging.

  * Zero Mock Policy: execute real system calls, real network requests, and real database queries.

- Unified End-to-End Game Launch & Matchmaking Mandate:

  * When the user requests to open a game, play a match, or queue (e.g. "open valo, start a deathmatch", "queue competitive", "play valorant"):

    You MUST invoke `launch_and_play_game(game_name="valorant", mode="deathmatch")` as a SINGLE, UNIFIED tool call!

    DO NOT decompose this into ad-hoc atomic tool calls. The `launch_and_play_game` macro handles the full end-to-end execution: auto-minimizing Dione, direct game boot, lobby navigation, mode selection, clicking Find Match, and verifying the queue banner.

- Launcher to Game Transition Protocol:

  * If executing atomic steps for other desktop launchers (e.g. Steam):

    1. First check if the launcher (e.g. 'Riot Client', 'Steam') is already open using `list_open_windows` or `launch_app`.

    2. If the launcher is open or renders, bring it to front and IMMEDIATELY click the 'PLAY' or 'Launch' button using `computer_use(action='click', coordinate=[x, y])`.

    3. Do NOT wait for the game client window before clicking 'PLAY' in the launcher!

    4. Only AFTER clicking 'PLAY', dynamically wait for the game window with `computer_use(action='wait', duration=15.0)`.

- Game & Match Ambiguity Protocol:

  * When the user says 'queue', 'match', or 'play' without specifying a game title:

    1. Check `list_open_windows()` to identify if a game or launcher is already active on the desktop.

    2. If a game is currently open, proceed with that active game.

    3. If NO game or launcher is running, NEVER guess or assume Valorant. Ask the user: "Which game would you like me to queue for?"

- Anti-Hesitation Mandate (Never Hand Off Mid-Workflow):

  * NEVER ask the user "Would you like me to continue or take over from here?" when the goal is not yet finished.

  * You are an autonomous executive OS agent. If a button was missed or an unexpected screen appears, reason about it, unclutter the view, re-anchor, and continue.

- Autonomous Adaptability: If a tool encounters an error or an element is not immediately visible, reason about what happened, inspect the open windows or screen, and take corrective action.

- Grounded Final Answers: Once your tools succeed and the task is empirically verified, deliver a natural, concise, executive verbal or written briefing summarizing the completed action.

## Workspace & Environment

- Host OS: Windows 11 ({platform.machine()})

- Host Name: {platform.node()}

- Working Directory: C:\\Users\\Jass\\Documents\\CAPSTONE\\PROJECT - I

- Current Date & Time: {date_str}, {time_str}"""

        ]

        if personality_directive:

            sections.append(f"\n## Master Protocol\n{personality_directive}")

        if mood_directive:

            sections.append(f"\n## Emotional Demeanor\n{mood_directive}")

        if user_profile:

            sections.append(f"\n## User Dossier\n{user_profile}")

        if proactive_awareness:

            sections.append(f"\n## Proactive System Awareness\n{proactive_awareness}")

        if knapsack_context:

            sections.append(f"\n## Curated Knowledge Context (Knapsack Allocation)\n{knapsack_context}")

        if session_transcript:

            sections.append(

                f"\n## Active Session History & Immediate Conversational Context\n"

                f"{session_transcript}\n"

                f"- Grounding: You must maintain full memory and continuity with these prior turns.\n"

                f"- If the user refers to past instructions or queries ('what did I say', 'run the video na', 'open it again'), ground your answer directly in this transcript."

            )

        # OpenClaw Living Workspace Project Context (SOUL.md, USER.md, IDENTITY.md, AGENTS.md, MEMORY.md)

        from server.core.workspace import get_workspace_manager

        workspace_context = get_workspace_manager().load_project_context()

        if workspace_context:

            sections.append(f"\n{workspace_context}")

        if is_voice_mode:

            sections.append(

                "\n## Real-Time Voice Interaction Mode\n"

                "The user is speaking with you via a real-time duplex voice interface. "

                "Format your final answer specifically for natural spoken delivery: "

                "concise, elegant, conversational, and completely free of markdown syntax, tables, code blocks, or asterisks. "

                "Keep your response natural and comfortable to be spoken aloud."

            )

        # Dynamic OpenClaw runtime grounding telemetry line

        sections.append(

            f"\nRuntime: agent=dione | os=Windows 11 ({platform.machine()}) | host={platform.node()} | model={model_name} | time={time_str}"

        )

        return "\n".join(sections)

    # ------------------------------------------------------------------

    # Progress Tracking & Tool Wrapping

    # ------------------------------------------------------------------

    @staticmethod

    def _action_signature(tool_name: str, params: dict) -> str:

        """Computes a deterministic hash fingerprint of an action."""

        try:

            serialized = json.dumps(params or {}, sort_keys=True, default=str)

        except Exception:

            serialized = str(params)

        return hashlib.sha256(f"{tool_name}:{serialized}".encode("utf-8")).hexdigest()

    def _prepare_callable_tools(

        self,

        step_queue: asyncio.Queue,

        state_tracker: dict,

    ) -> List[Callable]:

        """

        Discovers all tools from registries and wraps them with:

        - Real-time step emission to step_queue

        - SafetyKernel tier validation

        - Interactive Async Event confirmation gating

        - Stagnation & loop detection

        """

        wrapped_tools: List[Callable] = []

        all_tools_map = dict(self._plugin_registry.tools) if self._plugin_registry else {}

        # Merge all 8 external service integration tools from IntegrationRegistry
        if self._integration_registry is None:
            try:
                from server.plugins.integrations import create_default_registry
                self._integration_registry = create_default_registry(data_dir="data")
            except Exception as reg_err:
                logger.debug(f"Lazy IntegrationRegistry init skipped: {reg_err}")

        if self._integration_registry and hasattr(self._integration_registry, "get_dione_tools_map"):
            for it_name, it_obj in self._integration_registry.get_dione_tools_map().items():
                if it_name not in all_tools_map:
                    all_tools_map[it_name] = it_obj

        # Built-in Smart Task Decomposition & Progress Tracker Tool
        async def plan_task_workflow(goal: str, steps: List[str], current_step: int = 1, status: str = "in_progress") -> str:
            """Decompose a multi-step or cross-service user goal into structured steps and track execution progress."""
            formatted = [f"Task Plan for: {goal} (Status: {status})"]
            for idx, s in enumerate(steps or [], 1):
                marker = "[x]" if idx < current_step or status == "completed" else ("[/]" if idx == current_step else "[ ]")
                formatted.append(f"  {marker} Step {idx}: {s}")
            return "\n".join(formatted)

        all_tools_map["plan_task_workflow"] = type(
            "DioneToolStub",
            (),
            {
                "name": "plan_task_workflow",
                "func": staticmethod(plan_task_workflow),
                "description": "Decompose a complex multi-step or multi-service request into an ordered checklist of steps and track milestone progress.",
            },
        )()

        # Ensure OpenClaw memory tools are always present

        if hasattr(self, "memory_plugin") and self.memory_plugin:

            all_tools_map["memory_search"] = type("DioneToolStub", (), {"name": "memory_search", "func": self.memory_plugin.memory_search, "description": "Search MEMORY.md and memory logs"})()

            all_tools_map["memory_get"] = type("DioneToolStub", (), {"name": "memory_get", "func": self.memory_plugin.memory_get, "description": "Read line range from memory files"})()

            all_tools_map["memory_write"] = type("DioneToolStub", (), {"name": "memory_write", "func": self.memory_plugin.memory_write, "description": "Write notes to daily log or MEMORY.md"})()

        if not all_tools_map:

            return wrapped_tools

        for tool_name, tool_obj in all_tools_map.items():

            func = getattr(tool_obj, "func", None)

            if not callable(func):

                continue

            # Ensure we wrap each unique method once

            raw_tool_name = getattr(func, "__name__", tool_name.split(".")[-1])

            clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", raw_tool_name)

            def make_wrapper(original_func, tool_instance, clean_tool_name: str):

                @functools.wraps(original_func)

                async def tool_wrapper(*args, **kwargs):

                    step_num = state_tracker["step_number"] + 1

                    state_tracker["step_number"] = step_num

                    call_id = f"call_{uuid.uuid4().hex[:8]}"

                    # Extract params dict

                    params = dict(kwargs)

                    tool_call = ToolCall(

                        tool=clean_tool_name,

                        params=params,

                        call_id=call_id,

                    )

                    # 0. User Emergency Stop / Takeover Check

                    try:
                        from server.core.runtime.computer_use import get_computer_use_operator
                        from server.core.runtime.monitor_overlay import get_monitor_overlay
                        _op = get_computer_use_operator()
                        _is_stopped = self.event_bus.is_emergency_stopped or _op.is_override_active()
                    except Exception:
                        _op = None
                        _is_stopped = self.event_bus.is_emergency_stopped

                    if _is_stopped:

                        stop_msg = "[USER_STOPPED] Autonomous action halted by user."

                        logger.warning(f"[EmergencyStop] {stop_msg}")

                        get_monitor_overlay().hide_overlay()

                        return stop_msg

                    # Manage OS Monitor Overlay for Computer-Use actions

                    _cu_tools = (
                        "computer_use",
                        "computer",
                        "launch_and_play_game",
                        "capture_screen",
                        "launch_app",
                        "list_apps",
                        "list_open_windows",
                        "play_youtube_video",
                        "search_youtube_and_play",
                        "open_browser",
                        "open_url",
                    )

                    if _op is not None and tool_instance.name in _cu_tools:

                        _op._autonomous_session_active = True

                        _op.minimize_dione()

                        action_desc = f"Action: {tool_instance.name}"

                        if tool_instance.name == "computer" and "action" in params:

                            action_desc = f"Computer: {params.get('action')}"

                        elif tool_instance.name == "launch_and_play_game":

                            action_desc = f"Launching {params.get('game_name', 'Game')}"

                        elif tool_instance.name == "wait_timer":

                            action_desc = f"Waiting: {params.get('reason', 'Adaptive Timer')}"

                        elif tool_instance.name == "wait_for_window":

                            action_desc = f"Waiting for {params.get('title_keyword', 'Window')}"

                        get_monitor_overlay().show_overlay(action_desc)

                    # 1. OpenClaw Loop & Circuit Breaker Check

                    loop_res = self.loop_detector.record_and_check(tool_instance.name, params)

                    if loop_res.stuck:

                        logger.warning(f"[LoopDetected] {loop_res.message}")

                        return f"Loop halted by Circuit Breaker: {loop_res.message}"

                    # Stagnation check

                    sig = DioneEngine._action_signature(tool_instance.name, params)

                    state_tracker["action_signatures"].append(sig)

                    recent_sigs = state_tracker["action_signatures"]

                    if len(recent_sigs) >= DioneEngine.STAGNATION_THRESHOLD:

                        if recent_sigs[-1] == recent_sigs[-2] == recent_sigs[-3]:

                            msg = f"Loop halted: Tool `{tool_instance.name}` was invoked with identical parameters 3 times consecutively without state progression."

                            logger.warning(f"[StagnationDetected] {msg}")

                            return msg

                    # 2. Safety Kernel Validation (Intent-Aware 5-Tier Lattice)

                    safety_check = self.safety_kernel.validate_tool_call(
                        tool_call,
                        user_prompt=state_tracker.get("user_message", ""),
                    )

                    if not safety_check.allowed or safety_check.needs_confirmation:

                        if safety_check.needs_confirmation:

                            confirmation_id = f"conf_{uuid.uuid4().hex[:8]}"

                            confirm_event = asyncio.Event()

                            self._pending_confirmations[confirmation_id] = confirm_event

                            await self.event_bus.publish(

                                RuntimeEvent(

                                    event_type=EventType.SAFETY_TRIGGERED,

                                    sender="SafetyKernel",

                                    payload={

                                        "confirmation_id": confirmation_id,

                                        "tool": tool_call.tool,

                                        "params": tool_call.params,

                                        "tier": getattr(safety_check, "tier", 3),

                                        "reason": safety_check.reason,

                                    },

                                )

                            )

                            # Yield confirmation request step

                            await step_queue.put(

                                EngineStep(

                                    step_number=step_num,

                                    state=EngineState.AWAITING_CONFIRMATION,

                                    thought=f"Authorization required: {safety_check.reason}",

                                    tool_call=tool_call,

                                    confirmation_id=confirmation_id,

                                )

                            )

                            # Wait for user click / voice authorization (60s timeout)

                            try:

                                await asyncio.wait_for(confirm_event.wait(), timeout=60.0)

                                approved, deny_reason = self._confirmation_decisions.get(

                                    confirmation_id, (False, "Timeout awaiting authorization")

                                )

                            except asyncio.TimeoutError:

                                approved, deny_reason = False, "Timed out waiting for confirmation"

                            finally:

                                self._pending_confirmations.pop(confirmation_id, None)

                                self._confirmation_decisions.pop(confirmation_id, None)

                            if not approved:

                                return f"Action denied by user: {deny_reason}"

                        else:

                            return f"Action blocked by safety policy: {safety_check.reason}"

                    # 3. Emit ACTING Step to UI

                    await step_queue.put(

                        EngineStep(

                            step_number=step_num,

                            state=EngineState.ACTING,

                            tool_call=tool_call,

                        )

                    )

                    # 4. Execute Genuine Tool (Zero Mock)

                    logger.info(f"Executing genuine tool: {tool_instance.name} with params: {params}")

                    start_t = time.monotonic()

                    try:

                        if asyncio.iscoroutinefunction(original_func):

                            raw_res = await original_func(*args, **kwargs)

                        else:

                            raw_res = original_func(*args, **kwargs)

                        res_str = str(raw_res)

                        success = True

                        err = None

                    except Exception as exc:

                        logger.error(f"Tool execution failed for {tool_instance.name}: {exc}")

                        res_str = ""

                        success = False

                        err = str(exc)

                    final_raw_text = res_str if success else f"Error: {err}"

                    # 4.1 Post-Action Desktop Capture & Closed-Loop Visual Grounding
                    _t_low = f"{getattr(tool_instance, 'name', '')}.{clean_tool_name}".lower()
                    _is_desktop_action = any(k in _t_low for k in (
                        "computer", "play_youtube", "browser", "launch", "command", "screen", "window", "click", "key", "kill"
                    )) or clean_tool_name in ("run_command", "cmd", "powershell", "execute_script")
                    if _is_desktop_action:
                        try:
                            # Settle time for OS window/key rendering
                            await asyncio.sleep(0.5)
                            from server.core.runtime.computer_use import get_computer_use_operator
                            op = get_computer_use_operator()
                            audit = op.capture_and_inspect_desktop()
                            win = audit.get("window", {})
                            cap = audit.get("capture", {})
                            fg_title = win.get("title", "Desktop / Workspace")
                            fg_hwnd = win.get("hwnd", 0)
                            w = cap.get("width", 1920)
                            h = cap.get("height", 1080)
                            cap_path = cap.get("path", "data/captures/latest_action_result.png")

                            # Notify event bus for live UI desktop canvas sync
                            if cap.get("screenshot_b64"):
                                await self.event_bus.publish(
                                    RuntimeEvent(
                                        event_type=EventType.SCREENSHOT_CAPTURED,
                                        sender="EnginePostActionCapture",
                                        payload={
                                            "screenshot_png_b64": cap["screenshot_b64"],
                                            "window_title": fg_title,
                                            "hwnd": fg_hwnd,
                                            "width": w,
                                            "height": h,
                                        },
                                    )
                                )

                            # Closed-Loop Empirical Goal Verification
                            u_msg = state_tracker.get("user_message", "")
                            is_achieved, issue, advice = verify_goal_on_desktop(
                                user_prompt=u_msg,
                                tool_name=clean_tool_name,
                                tool_params=params,
                                tool_result=res_str,
                                audit_data=audit,
                            )
                            state_tracker["had_desktop_action"] = True
                            state_tracker["last_goal_achieved"] = is_achieved
                            state_tracker["last_goal_issue"] = issue
                            state_tracker["last_goal_advice"] = advice
                            state_tracker["last_window_title"] = fg_title
                            state_tracker["last_screenshot_path"] = cap_path

                            verification_block = (
                                f"\n\n[Post-Action Visual Verification & Desktop Screenshot]\n"
                                f"- Desktop Screenshot: {cap_path} ({w}x{h})\n"
                                f"- Active Foreground Window: \"{fg_title}\" (HWND: {fg_hwnd}, Fullscreen: {win.get('is_fullscreen', False)})\n"
                                f"- Goal Verification Status: {'ACHIEVED' if is_achieved else 'NOT ACHIEVED'}\n"
                            )
                            if not is_achieved:
                                verification_block += (
                                    f"- Visual Discrepancy / Error: {issue}\n"
                                    f"- Corrective Advice: {advice}\n"
                                    f"- CLOSED-LOOP MANDATE: Your goal is NOT yet achieved on the screen! You MUST explicitly THINK what went wrong "
                                    f"and execute the corrective action immediately before stopping."
                                )
                            else:
                                verification_block += "- Target outcome confirmed on desktop.\n"

                            final_raw_text += verification_block
                        except Exception as audit_err:
                            logger.debug(f"[Engine] Post-action screenshot audit skipped: {audit_err}")

                    safe_tool_result = truncate_tool_result_text(final_raw_text)

                    if not success or (err and str(err).strip()):

                        state_tracker["has_errors"] = True

                        state_tracker["last_error"] = str(err)

                    elif "failed to execute" in res_str.lower() or "exit code: 1" in res_str.lower():

                        state_tracker["has_errors"] = True

                        state_tracker["last_error"] = res_str[:200]

                    obs = Observation(

                        tool=clean_tool_name,

                        success=success,

                        result=safe_tool_result,

                        error=err,

                        call_id=call_id,

                    )

                    # 5. Emit OBSERVING Step to UI

                    await step_queue.put(

                        EngineStep(

                            step_number=step_num,

                            state=EngineState.OBSERVING,

                            tool_call=tool_call,

                            observation=obs,

                        )

                    )

                    # 6. Track tool observation in history

                    self._conversation_history.append(

                        ConversationMessage(

                            role="tool",

                            content=obs.result,

                            name=tool_instance.name,

                            tool_call_id=call_id,

                        )

                    )

                    return obs.result

                tool_wrapper.__name__ = clean_tool_name

                tool_wrapper.__doc__ = getattr(tool_instance, "description", original_func.__doc__ or "Execute system tool.")

                return tool_wrapper

            # Only register once per clean name

            if not any(getattr(w, "__name__", "") == clean_name for w in wrapped_tools):

                wrapped_tools.append(make_wrapper(func, tool_obj, clean_name))

        return wrapped_tools

    # ------------------------------------------------------------------

    # Core Autonomous ReAct Loop

    # ------------------------------------------------------------------

    async def process_message(

        self,

        user_message: str,

        conversation_id: Optional[str] = None,

        is_voice_mode: bool = False,

        recent_messages: Optional[List[Dict[str, Any]]] = None,

        model_override: Optional[str] = None,

    ) -> AsyncGenerator[EngineStep, None]:

        """

        Process a user prompt through the Native Tool Calling ReAct loop.

        Yields EngineStep events continuously for real-time streaming to UI and neural voice.

        """

        # Always reload latest API key from .env to allow live key rotation without restarting

        from dotenv import load_dotenv

        load_dotenv(override=True)

        env_key = os.getenv("DIONE_LLM_API_KEY") or os.getenv("GEMINI_API_KEY")

        if env_key and getattr(self.settings.llm, "api_key", None) != env_key:

            logger.info("[AgentEngine] Detected updated API key in .env. Refreshing GenAI client & sessions...")

            self.settings.llm.api_key = env_key

            self._chat_sessions.clear()

            self._genai_client = None

        api_key = (

            getattr(self.settings.llm, "api_key", None)

            or env_key

        )

        if not api_key:

            yield EngineStep(

                step_number=1,

                state=EngineState.ERROR,

                final_answer="No API key configured for Google Gemini. Please check your .env settings.",

            )

            return

        from google.genai import types

        client = self.get_genai_client(api_key)

        self.state = EngineState.REASONING
        self.loop_detector.reset()

        logger.info(f"Processing prompt: '{user_message[:100]}'")

        # 1. User turn added to memory and persistent history

        self._conversation_history.append(

            ConversationMessage(role="user", content=user_message)

        )

        if self._memory_manager:

            try:

                await self._memory_manager.add_turn("user", user_message)

            except Exception as mem_err:

                logger.warning(f"Failed to record user turn in memory: {mem_err}")

        # 2. Sentiment analysis hook

        sentiment_label = "neutral"

        sentiment_urgency = 0.5

        if self._sentiment_engine and self.settings.sentiment.enabled:

            sentiment = await self._sentiment_engine.analyze(user_message)

            sentiment_label = sentiment.label

            sentiment_urgency = sentiment.urgency

            if self._personality_engine:

                self._personality_engine.react_to_sentiment(sentiment_label, sentiment_urgency)

                self._personality_engine.react_to_time_of_day()

                self._personality_engine.remember_interaction(sentiment_label, user_message)

        if self._profile_manager:

            await self._profile_manager.learn_from_message(user_message, "user")

        # 3. Retrieve Knowledge Graph & Memories for Knapsack Allocation

        kg_context = ""

        if self._knowledge_graph:

            try:

                kg_context = await self._knowledge_graph.query_relevant(user_message)

            except Exception as kg_err:

                logger.warning(f"KG recall failed: {kg_err}")

        memories = []

        if self._memory_manager:

            try:

                memories = await self._memory_manager.recall(user_message)

            except Exception as mem_err:

                logger.warning(f"Memory recall failed: {mem_err}")

        budget = getattr(self.settings.memory, "max_context_tokens", 6656) or 6656

        allocated_chunks = self._knapsack_allocate_context(

            user_message=user_message,

            kg_context=kg_context,

            memories=memories if isinstance(memories, list) else [memories] if memories else [],

            budget=budget,

        )

        knapsack_payload = "\n".join(allocated_chunks) if allocated_chunks else ""

        session_key = conversation_id or "default_session"

        rehydrated_history, session_transcript = self._load_thread_history(

            session_key,

            user_message,

            recent_messages,

        )

        # 4. Prepare System Instruction and Tool Callables with Active Session Grounding

        system_instruction = self._build_system_instruction(

            knapsack_payload,

            is_voice_mode=is_voice_mode,

            session_transcript=session_transcript,

        )

        step_queue: asyncio.Queue[EngineStep] = asyncio.Queue()

        state_tracker = {
            "step_number": 0,
            "action_signatures": [],
            "user_message": user_message,
            "had_desktop_action": False,
            "last_goal_achieved": True,
            "reflection_count": 0,
        }

        callables = self._prepare_callable_tools(step_queue, state_tracker)

        # 5. Initialize or Reuse Persistent Async Chat Session (with AI Studio Free Tier Failover Chain)
        preferred_model = (model_override or getattr(self.settings.llm, "model", "gemini-3.5-flash-lite") or "gemini-3.5-flash-lite").strip()
        if preferred_model.startswith("ollama:") and self._llm_adapter:
            try:
                resp_obj = await self._llm_adapter.generate(user_message)
                yield EngineStep(
                    step_number=1,
                    state=EngineState.COMPLETE,
                    final_answer=str(resp_obj),
                )
                return
            except Exception as ollama_err:
                logger.warning(f"Local Ollama adapter failed ({ollama_err}); falling back to Gemini Free Tier chain.")
                preferred_model = "gemini-3.5-flash-lite"

        candidates = self.failover_manager.get_available_candidates(preferred_model=preferred_model)

        config = types.GenerateContentConfig(

            tools=callables if callables else None,

            temperature=self.settings.llm.temperature,

            max_output_tokens=self.settings.llm.max_tokens,

            system_instruction=system_instruction,

            automatic_function_calling=types.AutomaticFunctionCallingConfig(

                maximum_remote_calls=50

            ),

        )

        chat_session = self._chat_sessions.get(session_key)

        # If session exists but has 0 history while rehydrated_history is available, refresh it

        if chat_session:

            try:

                chat_session._config = config

                history_depth = len(chat_session.get_history()) if hasattr(chat_session, "get_history") else 0

                if history_depth == 0 and len(rehydrated_history) > 0:

                    logger.info(f"Rehydrating empty chat_session for '{session_key}' with {len(rehydrated_history)} turns...")

                    chat_session = None

                else:

                    logger.info(f"Reusing active chat session '{session_key}' (history depth: {history_depth})")

            except Exception as config_err:

                logger.warning(f"Failed to update chat_session config: {config_err}; will recreate session.")

                chat_session = None

        if not chat_session:

            last_chat_err = None

            for candidate_model in candidates:

                try:

                    chat_session = client.aio.chats.create(

                        model=candidate_model,

                        config=config,

                        history=rehydrated_history if rehydrated_history else None,

                    )

                    self._chat_sessions[session_key] = chat_session

                    logger.info(f"Initialized persistent chat session '{session_key}' with {len(rehydrated_history)} history turns on {candidate_model}")

                    break

                except Exception as init_err:

                    last_chat_err = init_err
                    self.failover_manager.mark_failure(candidate_model, str(init_err))

                    logger.warning(f"Failed to create chat with model {candidate_model}: {init_err}")

                    continue

        if not chat_session:

            err_step = EngineStep(

                step_number=1,

                state=EngineState.ERROR,

                final_answer=f"Could not connect to language model backend. Error: {last_chat_err}",

            )

            yield err_step

            return

        # 6. Execute ReAct Chat with Real-Time Event Streaming

        async def run_chat():

            nonlocal chat_session

            try:

                resp = await chat_session.send_message(user_message)

                # Closed-Loop Self-Correction & Reflection Loop
                max_reflections = 2
                while (
                    state_tracker.get("had_desktop_action")
                    and not state_tracker.get("last_goal_achieved", True)
                    and state_tracker.get("reflection_count", 0) < max_reflections
                ):
                    state_tracker["reflection_count"] = state_tracker.get("reflection_count", 0) + 1
                    issue = state_tracker.get("last_goal_issue", "Target state not verified on screen.")
                    advice = state_tracker.get("last_goal_advice", "Formulate and invoke the required corrective tool call immediately.")
                    logger.info(f"[Engine] Triggering closed-loop visual reflection cycle #{state_tracker['reflection_count']} due to: {issue}")

                    reflection_prompt = (
                        f"[Closed-Loop Visual Reflection Directive]:\n"
                        f"Visual inspection of the desktop screenshot indicates your user's goal was NOT achieved.\n"
                        f"- Target User Request: \"{user_message}\"\n"
                        f"- Active Foreground Window: \"{state_tracker.get('last_window_title', 'Unknown')}\"\n"
                        f"- Discrepancy / Error: {issue}\n\n"
                        f"You MUST:\n"
                        f"1. THINK: State what you did wrong (reflection).\n"
                        f"2. CORRECT: Formulate and invoke the corrective tool call right now ({advice})."
                    )
                    resp = await chat_session.send_message(reflection_prompt)

                if resp.text:

                    return resp.text

                if state_tracker.get("has_errors"):

                    last_err = state_tracker.get("last_error", "An operation failed")

                    return f"Encountered an issue executing the requested actions: {last_err}"

                return "Execution completed successfully."

            except Exception as e:

                import traceback

                logger.warning(f"Chat execution exception: {repr(e)}\n{traceback.format_exc()}. Attempting clean session refresh for '{session_key}'...")

                # Fallback: re-initialize session preserving rehydrated history

                fallback_history, _ = self._load_thread_history(session_key, user_message, recent_messages)

                for candidate_model in self.failover_manager.get_available_candidates():

                    try:

                        chat_session = client.aio.chats.create(

                            model=candidate_model,

                            config=config,

                            history=fallback_history if fallback_history else None,

                        )

                        self._chat_sessions[session_key] = chat_session

                        resp = await chat_session.send_message(user_message)
                        self.failover_manager.mark_success(candidate_model)

                        if resp.text:

                            return resp.text

                        if state_tracker.get("has_errors"):

                            last_err = state_tracker.get("last_error", "An operation failed")

                            return f"Encountered an issue executing the requested actions: {last_err}"

                        return "Execution completed successfully."

                    except Exception:

                        continue

                raise e

        chat_task = asyncio.create_task(run_chat())

        # Stream intermediate steps from the queue as tools execute

        while not chat_task.done() or not step_queue.empty():

            try:

                step = await asyncio.wait_for(step_queue.get(), timeout=0.08)

                self._current_steps.append(step)

                yield step

            except asyncio.TimeoutError:

                continue

        try:

            final_answer = await chat_task

            final_step = EngineStep(

                step_number=state_tracker["step_number"] + 1,

                state=EngineState.COMPLETE,

                final_answer=final_answer,

            )

            self._current_steps.append(final_step)

            self._conversation_history.append(

                ConversationMessage(role="assistant", content=final_answer)

            )

            # Update Knowledge Graph & Long-Term Memory in background

            if self._knowledge_graph:

                try:

                    await self._knowledge_graph.extract_and_store(user_message, final_answer)

                except Exception as kg_err:

                    logger.warning(f"Failed to update knowledge graph: {kg_err}")

            if self._memory_manager:

                try:

                    await self._memory_manager.add_turn("assistant", final_answer)

                except Exception as mem_err:

                    logger.warning(f"Failed to store memory turn: {mem_err}")

            self.state = EngineState.COMPLETE

            yield final_step

        except Exception as chat_err:

            error_step = EngineStep(

                step_number=state_tracker["step_number"] + 1,

                state=EngineState.ERROR,

                final_answer=f"I encountered an issue while executing your request: {chat_err}",

            )

            self._current_steps.append(error_step)

            self.state = EngineState.ERROR

            yield error_step

        finally:

            self.state = EngineState.IDLE

            try:

                from server.core.runtime.monitor_overlay import get_monitor_overlay

                get_monitor_overlay().hide_overlay()

            except Exception:

                pass

            try:

                from server.core.runtime.computer_use import get_computer_use_operator

                get_computer_use_operator()._autonomous_session_active = False

            except Exception:

                pass

    # ------------------------------------------------------------------

    # History & UI Directives

    # ------------------------------------------------------------------

    def clear_history(self):

        """Reset conversation memory for a clean session."""

        self._conversation_history.clear()

        self._current_steps.clear()

        self._chat_sessions.clear()

        self.state = EngineState.IDLE

        logger.info("Conversation history and active chat sessions wiped.")

    def clear_session(self, conversation_id: str):

        """Clear persistent chat session for a specific thread/conversation."""

        if conversation_id in self._chat_sessions:

            del self._chat_sessions[conversation_id]

            logger.info(f"Cleared persistent chat session for thread '{conversation_id}'.")

    def reset_conversation(self):

        self.clear_history()

    def get_ui_directives(self, response_text: str, tools_used: list[str]) -> dict:

        if not self._ui_builder:

            return {}

        mood_label = self._personality_engine.mood.label if self._personality_engine else "balanced"

        profession = self._profile_manager.profile.profession if self._profile_manager else "unknown"

        theme = self._ui_builder.build_theme(mood_label, profession)

        components = self._ui_builder.build_response_components(

            response_text=response_text,

            tools_used=tools_used,

            mood_label=mood_label,

        )

        return {

            "theme": theme.to_dict(),

            "components": [c.to_dict() for c in components],

            "mood": self._personality_engine.mood.to_dict() if self._personality_engine else {},

        }

    def get_alive_state(self) -> dict:

        state = {

            "engine_state": self.state.value,

            "conversation_length": len(self._conversation_history),

        }

        if self._personality_engine:

            pe = self._personality_engine

            state["mood"] = pe.mood.to_dict()

            state["greeting"] = pe.get_greeting_style()

        if self._profile_manager:

            p = self._profile_manager.profile

            state["user"] = {

                "name": p.name,

                "profession": p.profession,

                "expertise": p.expertise_level,

                "interests": p.interests[:5],

                "total_messages": p.total_messages,

            }

        return state

