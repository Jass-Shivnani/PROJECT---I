"""
Dione AI — Sovereign Pure-Native Desktop Application
=====================================================
A 100% native desktop application for Windows built with CustomTkinter:
- ZERO WebView2 runtime / ZERO browser DOM overhead
- Native hardware-accelerated Windows widgets with dark Obsidian theme
- Real-time conversation streaming with ReAct thought disclosure and tool execution cards
- Interactive Poset Lattice 1-click Approval Banner for Tier 4 (PRIVILEGED) actions
- Live hardware telemetry dock (CPU, RAM, Battery, NVIDIA GPU, Uptime)
- Autonomous Computer-Use On-Screen Floating HUD with physical mouse fail-safe lockout
- Seamless Windows System Tray minimization
"""

import os
import sys
import time
import json
import asyncio
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

# Windows event loop policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import customtkinter as ctk
import psutil
from PIL import Image, ImageDraw
import pystray
from loguru import logger

from server.core.engine import DioneEngine, EngineState, EngineStep
from server.core.safety import SafetyKernel, PermissionTier
from server.plugins.registry import PluginRegistry
from server.knowledge.graph import KnowledgeGraph
from server.memory.manager import MemoryManager
from server.memory.vectorstore import VectorStore
from server.memory.embeddings import EmbeddingService
from server.sentiment.analyzer import SentimentAnalyzer
from server.personality.profile import UserProfileManager
from server.personality.engine import PersonalityEngine
from server.personality.ui_components import UIDirectiveBuilder
from server.proactive.heartbeat import HeartbeatScheduler
from server.proactive.dream_engine import DreamSynthesisEngine
from server.core.runtime.computer_use import get_computer_use_operator
from server.config.settings import get_settings


# ----------------------------------------------------------------------
# Floating Computer-Use HUD
# ----------------------------------------------------------------------
class ComputerUseHUD:
    """Floating on-screen HUD shown when Dione is actively controlling the PC."""

    def __init__(self):
        self._window: Optional[ctk.CTkToplevel] = None
        self._label: Optional[ctk.CTkLabel] = None
        self._is_visible = False

    def show(self, master, action_name: str = "Desktop Automation"):
        if self._is_visible and self._window:
            self.update_action(action_name)
            return

        try:
            self._window = ctk.CTkToplevel(master)
            self._window.overrideredirect(True)
            self._window.attributes("-topmost", True)
            self._window.attributes("-alpha", 0.94)

            # Center top positioning
            screen_w = master.winfo_screenwidth()
            hud_w, hud_h = 560, 52
            x = (screen_w - hud_w) // 2
            y = 24
            self._window.geometry(f"{hud_w}x{hud_h}+{x}+{y}")
            self._window.configure(fg_color="#090d16")

            frame = ctk.CTkFrame(self._window, fg_color="#090d16", corner_radius=12, border_width=2, border_color="#e11d48")
            frame.pack(fill="both", expand=True, padx=2, pady=2)

            self._label = ctk.CTkLabel(
                frame,
                text=f"🔴 Dione in Autonomous Control — [{action_name}] | Hands Off (Move mouse to abort)",
                font=("Segoe UI", 12, "bold"),
                text_color="#f43f5e",
            )
            self._label.pack(expand=True, pady=4)
            self._is_visible = True
        except Exception as e:
            logger.debug(f"[HUD] Could not display floating HUD: {e}")

    def update_action(self, action_name: str):
        if self._label and self._is_visible:
            try:
                self._label.configure(text=f"🔴 Dione in Autonomous Control — [{action_name}] | Hands Off (Move mouse to abort)")
            except Exception:
                pass

    def notify_override(self):
        if self._label and self._is_visible:
            try:
                self._label.configure(
                    text="⚠️ Physical Override Detected — AI Autonomous Control Halted!",
                    text_color="#fbbf24",
                )
            except Exception:
                pass

    def hide(self):
        if self._window and self._is_visible:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None
            self._label = None
            self._is_visible = False


# ----------------------------------------------------------------------
# Pure Native Desktop Application Window
# ----------------------------------------------------------------------
class DioneNativeApp(ctk.CTk):
    """Sovereign Native Desktop Application for Dione AI."""

    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("Dione AI — Sovereign Personal Assistant")
        self.geometry("1320x840")
        self.minsize(1000, 680)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color="#070a12")

        # Core State & Background Event Loop
        self.engine: Optional[DioneEngine] = None
        self.safety = SafetyKernel()
        self.computer_use = get_computer_use_operator()
        self.hud = ComputerUseHUD()

        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_thread: Optional[threading.Thread] = None
        self._is_processing = False
        self._tray_icon = None

        # Build UI Structure
        self._build_header()
        self._build_body()
        self._build_approval_banner()
        self._build_composer()

        # Start Async Worker Engine
        self._start_async_worker()

        # Start Telemetry Poller
        self._start_telemetry_loop()

        # Bind window close to minimize to tray
        self.protocol("WM_DELETE_WINDOW", self.on_minimize_to_tray)
        self._setup_system_tray()

    def _build_header(self):
        """Top navigation and telemetry header."""
        self.header = ctk.CTkFrame(self, height=56, fg_color="#0b101d", corner_radius=0)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        # Brand & Iris
        brand_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        brand_frame.pack(side="left", padx=16, pady=8)

        self.iris_badge = ctk.CTkLabel(
            brand_frame,
            text="●",
            font=("Segoe UI", 18, "bold"),
            text_color="#06b6d4",
        )
        self.iris_badge.pack(side="left", padx=(0, 8))

        brand_label = ctk.CTkLabel(
            brand_frame,
            text="DIONE AI",
            font=("Segoe UI", 15, "bold"),
            text_color="#f8fafc",
        )
        brand_label.pack(side="left")

        version_pill = ctk.CTkLabel(
            brand_frame,
            text="SOVEREIGN OS",
            font=("Segoe UI", 9, "bold"),
            text_color="#94a3b8",
            fg_color="#172033",
            corner_radius=4,
            padx=6,
            pady=2,
        )
        version_pill.pack(side="left", padx=(8, 0))

        # Model & Engine Status
        self.status_pill = ctk.CTkLabel(
            self.header,
            text="Connecting Neural Core...",
            font=("Segoe UI", 11),
            text_color="#cbd5e1",
            fg_color="#111827",
            corner_radius=6,
            padx=10,
            pady=4,
        )
        self.status_pill.pack(side="left", padx=20)

        # Live Hardware Telemetry
        self.telemetry_pill = ctk.CTkLabel(
            self.header,
            text="CPU: --% | RAM: --GB | BAT: --%",
            font=("Consolas", 11),
            text_color="#38bdf8",
            fg_color="#0f172a",
            corner_radius=6,
            padx=12,
            pady=4,
        )
        self.telemetry_pill.pack(side="right", padx=16)

    def _build_body(self):
        """Main body layout: left sidebar + center chat stream."""
        self.body = ctk.CTkFrame(self, fg_color="#070a12", corner_radius=0)
        self.body.pack(fill="both", expand=True, side="top")

        # Left Sidebar
        self.sidebar = ctk.CTkFrame(self.body, width=220, fg_color="#0b101d", corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        sidebar_title = ctk.CTkLabel(self.sidebar, text="COMMAND MODES", font=("Segoe UI", 10, "bold"), text_color="#64748b")
        sidebar_title.pack(anchor="w", padx=16, pady=(16, 8))

        modes = [
            ("💬 Chat & Tasks", lambda: None),
            ("🧠 Memory & Knowledge", self._show_knowledge_view),
            ("🖥️ Screen & Windows", self._show_screen_view),
            ("🛡️ 5-Tier Safety Lattice", self._show_safety_view),
            ("🌙 Trigger Dream Mode", self._trigger_dream_mode),
        ]
        for name, cmd in modes:
            btn = ctk.CTkButton(
                self.sidebar,
                text=name,
                anchor="w",
                font=("Segoe UI", 12),
                fg_color="transparent",
                hover_color="#1e293b",
                text_color="#e2e8f0",
                height=36,
                command=cmd,
            )
            btn.pack(fill="x", padx=8, pady=2)

        # Chat Message Stream Frame
        self.chat_frame = ctk.CTkScrollableFrame(self.body, fg_color="#070a12", corner_radius=0)
        self.chat_frame.pack(side="right", fill="both", expand=True, padx=12, pady=12)

        # Welcome Card
        self._add_assistant_message(
            "Greetings, Sir. I am Dione, your sovereign personal assistant. "
            "I operate with genuine native system function calling, deep multi-turn execution, "
            "and active computer-use controls under your strict 5-Tier Poset Lattice guardrails. "
            "How may I assist you this evening?"
        )

    def _build_approval_banner(self):
        """Interactive 1-click confirmation banner for Tier 4 (PRIVILEGED) tool executions."""
        self.approval_banner = ctk.CTkFrame(self, height=64, fg_color="#1e1b4b", corner_radius=8, border_width=1, border_color="#6366f1")
        # Hidden by default
        self._pending_confirmation_id: Optional[str] = None

        self.approval_label = ctk.CTkLabel(
            self.approval_banner,
            text="⚠️ GATED ACTION: Confirmation Required",
            font=("Segoe UI", 11, "bold"),
            text_color="#c7d2fe",
        )
        self.approval_label.pack(side="left", padx=16)

        btn_box = ctk.CTkFrame(self.approval_banner, fg_color="transparent")
        btn_box.pack(side="right", padx=16)

        self.deny_btn = ctk.CTkButton(
            btn_box,
            text="Deny",
            width=80,
            height=28,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=("Segoe UI", 11, "bold"),
            command=self._on_deny_action,
        )
        self.deny_btn.pack(side="left", padx=6)

        self.approve_btn = ctk.CTkButton(
            btn_box,
            text="Approve Action",
            width=120,
            height=28,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            font=("Segoe UI", 11, "bold"),
            command=self._on_approve_action,
        )
        self.approve_btn.pack(side="left", padx=6)

    def _build_composer(self):
        """Bottom prompt input composer."""
        self.composer_frame = ctk.CTkFrame(self, height=80, fg_color="#0b101d", corner_radius=0)
        self.composer_frame.pack(fill="x", side="bottom")

        self.entry = ctk.CTkEntry(
            self.composer_frame,
            placeholder_text="Instruct Dione (e.g. 'What time is it?', 'Inspect screen', 'Run system diagnostic')...",
            font=("Segoe UI", 13),
            fg_color="#131b2e",
            text_color="#f8fafc",
            border_color="#1e293b",
            height=44,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(16, 8), pady=16)
        self.entry.bind("<Return>", lambda e: self.send_message())

        self.send_button = ctk.CTkButton(
            self.composer_frame,
            text="Execute",
            width=90,
            height=44,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=("Segoe UI", 12, "bold"),
            command=self.send_message,
        )
        self.send_button.pack(side="right", padx=(0, 16), pady=16)

    # ------------------------------------------------------------------
    # Async Engine Background Thread
    # ------------------------------------------------------------------
    def _start_async_worker(self):
        def _runner():
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
            self._async_loop.run_until_complete(self._initialize_core_engine())
            self._async_loop.run_forever()

        self._async_thread = threading.Thread(target=_runner, daemon=True, name="DioneAsyncEngine")
        self._async_thread.start()

    async def _initialize_core_engine(self):
        """Initialize all Dione subsystems in the background event loop."""
        try:
            settings = get_settings()
            from server.llm.gemini import GeminiAdapter
            llm = GeminiAdapter(api_key=settings.llm.api_key, model=settings.llm.model)

            embeddings = EmbeddingService(model_name=settings.vectorstore.embedding_model)
            vectorstore = VectorStore(persist_dir="data/vectorstore", embedding_service=embeddings)
            await vectorstore.initialize()

            memory = MemoryManager(data_dir="data/memory", vectorstore=vectorstore)
            await memory.initialize()

            knowledge = KnowledgeGraph(storage_path="data/knowledge_graph.json")
            sentiment = SentimentAnalyzer(mode="local")
            await sentiment.initialize()

            plugins = PluginRegistry()
            await plugins.load_plugins()

            profile = UserProfileManager(data_dir="data")
            personality = PersonalityEngine(data_dir="data")
            heartbeat = HeartbeatScheduler(data_dir="data")
            ui_builder = UIDirectiveBuilder()

            # Initialize DioneEngine
            self.engine = DioneEngine()
            self.engine.set_llm(llm)
            self.engine.set_plugins(plugins)
            self.engine.set_knowledge_graph(knowledge)
            self.engine.set_sentiment_engine(sentiment)
            self.engine.set_memory_manager(memory)
            self.engine.set_profile_manager(profile)
            self.engine.set_personality_engine(personality)
            self.engine.set_heartbeat(heartbeat)
            self.engine.set_ui_builder(ui_builder)

            self.after(0, lambda: self.status_pill.configure(
                text=f"Neural Core Active | {settings.llm.model}",
                text_color="#34d399",
            ))
            logger.info("[NativeApp] Core Dione Engine initialized cleanly.")
        except Exception as e:
            logger.error(f"[NativeApp] Failed to initialize core engine: {e}")
            self.after(0, lambda: self.status_pill.configure(text=f"Init Error: {e}", text_color="#f87171"))

    # ------------------------------------------------------------------
    # Message Dispatch & Execution
    # ------------------------------------------------------------------
    def send_message(self):
        text = self.entry.get().strip()
        if not text or self._is_processing:
            return

        self.entry.delete(0, "end")
        self._add_user_message(text)
        self._is_processing = True
        self.send_button.configure(state="disabled")

        # Run in background loop
        asyncio.run_coroutine_threadsafe(self._process_message_async(text), self._async_loop)

    async def _process_message_async(self, prompt: str):
        if not self.engine:
            self.after(0, lambda: self._add_assistant_message("Error: Neural core is still initializing. Please wait."))
            self.after(0, lambda: self.send_button.configure(state="normal"))
            self._is_processing = False
            return

        current_bubble = None

        try:
            async for step in self.engine.process_message(prompt):
                # Step: Thought disclosure
                if step.thought:
                    self.after(0, lambda t=step.thought: self._add_thought_disclosure(t))

                # Step: Tool Call Triggered
                if step.tool_call:
                    tool_name = step.tool_call.tool
                    self.after(0, lambda n=tool_name: self._add_tool_call_badge(n))
                    # If computer use action, show floating HUD
                    if any(kw in tool_name.lower() for kw in ["click", "launch", "type", "hotkey", "volume", "screen"]):
                        self.after(0, lambda n=tool_name: self.hud.show(self, n))

                # Step: Tool Observation
                if step.observation:
                    obs_text = step.observation.result[:300]
                    self.after(0, lambda o=obs_text: self._add_tool_result_badge(o))
                    self.after(0, lambda: self.hud.hide())

                # Step: Awaiting confirmation (Tier 4 / PRIVILEGED)
                if step.state == EngineState.AWAITING_CONFIRMATION and step.tool_call:
                    tool_desc = f"{step.tool_call.tool} with args: {step.tool_call.params}"
                    self.after(0, lambda d=tool_desc: self._show_approval_banner(d))

                # Step: Final Answer
                if step.state == EngineState.COMPLETE and step.final_answer:
                    ans = step.final_answer
                    self.after(0, lambda a=ans: self._add_assistant_message(a))

        except Exception as e:
            logger.error(f"[NativeApp] Message processing error: {e}")
            self.after(0, lambda: self._add_assistant_message(f"Sir, I encountered an operational fault: {e}"))
        finally:
            self.after(0, lambda: self.hud.hide())
            self.after(0, lambda: self.send_button.configure(state="normal"))
            self._is_processing = False

    # ------------------------------------------------------------------
    # Message Rendering Components
    # ------------------------------------------------------------------
    def _add_user_message(self, text: str):
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="#1e293b", corner_radius=10)
        msg_frame.pack(anchor="e", padx=12, pady=6, fill="x")

        lbl = ctk.CTkLabel(msg_frame, text=f"You: {text}", font=("Segoe UI", 12), text_color="#f8fafc", wraplength=700, justify="left")
        lbl.pack(padx=14, pady=8, anchor="w")

    def _add_assistant_message(self, text: str):
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="#0f172a", corner_radius=10, border_width=1, border_color="#1e293b")
        msg_frame.pack(anchor="w", padx=12, pady=6, fill="x")

        lbl = ctk.CTkLabel(msg_frame, text=f"Dione: {text}", font=("Segoe UI", 12), text_color="#cbd5e1", wraplength=760, justify="left")
        lbl.pack(padx=14, pady=10, anchor="w")

    def _add_thought_disclosure(self, thought: str):
        thought_frame = ctk.CTkFrame(self.chat_frame, fg_color="#0b1120", corner_radius=6)
        thought_frame.pack(anchor="w", padx=18, pady=2, fill="x")

        lbl = ctk.CTkLabel(
            thought_frame,
            text=f"💭 Thought: {thought[:180]}...",
            font=("Segoe UI", 10, "italic"),
            text_color="#94a3b8",
            wraplength=700,
            justify="left",
        )
        lbl.pack(padx=8, pady=4, anchor="w")

    def _add_tool_call_badge(self, tool_name: str):
        badge_frame = ctk.CTkFrame(self.chat_frame, fg_color="#172554", corner_radius=6)
        badge_frame.pack(anchor="w", padx=20, pady=2)

        lbl = ctk.CTkLabel(
            badge_frame,
            text=f"⚙️ Tool Call: {tool_name}",
            font=("Consolas", 10, "bold"),
            text_color="#60a5fa",
        )
        lbl.pack(padx=8, pady=3)

    def _add_tool_result_badge(self, result_text: str):
        badge_frame = ctk.CTkFrame(self.chat_frame, fg_color="#052e16", corner_radius=6)
        badge_frame.pack(anchor="w", padx=20, pady=2, fill="x")

        lbl = ctk.CTkLabel(
            badge_frame,
            text=f"✓ Result: {result_text.strip()[:140]}",
            font=("Consolas", 10),
            text_color="#4ade80",
            wraplength=700,
            justify="left",
        )
        lbl.pack(padx=8, pady=3, anchor="w")

    # ------------------------------------------------------------------
    # Approval Banner Handling
    # ------------------------------------------------------------------
    def _show_approval_banner(self, action_desc: str):
        self.approval_label.configure(text=f"⚠️ GATED ACTION: {action_desc[:70]}...")
        self.approval_banner.pack(fill="x", side="bottom", padx=16, pady=(0, 4))

    def _on_approve_action(self):
        self.approval_banner.pack_forget()
        if self.engine and self._async_loop:
            asyncio.run_coroutine_threadsafe(self.engine.confirm_action(confirmed=True), self._async_loop)

    def _on_deny_action(self):
        self.approval_banner.pack_forget()
        if self.engine and self._async_loop:
            asyncio.run_coroutine_threadsafe(self.engine.confirm_action(confirmed=False), self._async_loop)

    # ------------------------------------------------------------------
    # Telemetry Auto-Poller
    # ------------------------------------------------------------------
    def _start_telemetry_loop(self):
        def _poll():
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                vmem = psutil.virtual_memory()
                ram_used = round(vmem.used / (1024**3), 1)
                ram_total = round(vmem.total / (1024**3), 1)
                batt = psutil.sensors_battery()
                batt_str = f"{batt.percent}%" if batt else "AC"

                text = f"CPU: {cpu:.0f}% | RAM: {ram_used}/{ram_total}GB | BAT: {batt_str}"
                self.telemetry_pill.configure(text=text)
            except Exception:
                pass
            self.after(3000, _poll)

        self.after(2000, _poll)

    # ------------------------------------------------------------------
    # Sidebar Actions
    # ------------------------------------------------------------------
    def _show_knowledge_view(self):
        self._add_assistant_message("Inspecting Knowledge Graph & Memory Store...")
        if self.engine and self.engine._knowledge_graph:
            count = len(self.engine._knowledge_graph.graph.nodes)
            self._add_assistant_message(f"Knowledge Graph currently maintains {count} sovereign entities and relations.")

    def _show_screen_view(self):
        self._add_assistant_message("Triggering Multimodal Desktop Screen Inspection...")
        self.entry.delete(0, "end")
        self.entry.insert(0, "Take a screenshot and describe the active windows on screen.")
        self.send_message()

    def _show_safety_view(self):
        self._add_assistant_message(
            "🛡️ 5-Tier Poset Permission Lattice Status:\n"
            "  • Tier 0 (NONE): Blocked\n"
            "  • Tier 1 (READ): Auto-Approved (Date, System Info, Search)\n"
            "  • Tier 2 (INSPECT): Auto-Approved (Process List, File Metadata)\n"
            "  • Tier 3 (EXECUTE): Safe Assistant Actions (Launch App, Safe Shell Commands)\n"
            "  • Tier 4 (PRIVILEGED): Gated with 1-Click User Confirmation Banner\n"
            "  • Tier 5 (CATASTROPHIC): Blocked / Format C / Protected PID Shield"
        )

    def _trigger_dream_mode(self):
        self._add_assistant_message("Triggering Inactive Autonomous Scout & Research Cycle...")
        if self._async_loop:
            async def _run_dream():
                engine = DreamSynthesisEngine(knowledge_graph=self.engine._knowledge_graph, memory_manager=self.engine._memory_manager)
                await engine.trigger_cycle(reason="User Native App Trigger")
                briefing = engine.get_morning_briefing()
                self.after(0, lambda: self._add_assistant_message(f"Executive Morning Briefing:\n{briefing}"))
            asyncio.run_coroutine_threadsafe(_run_dream(), self._async_loop)

    # ------------------------------------------------------------------
    # System Tray Integration
    # ------------------------------------------------------------------
    def _setup_system_tray(self):
        def _create_tray_image():
            img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((4, 4, 60, 60), fill=(109, 40, 217, 255), outline=(139, 92, 246, 255), width=2)
            draw.ellipse((16, 16, 48, 48), fill=(6, 182, 212, 255), outline=(103, 232, 249, 255), width=2)
            draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 255))
            return img

        menu = pystray.Menu(
            pystray.MenuItem("Open Dione", lambda icon, item: self.after(0, self.on_restore_from_tray), default=True),
            pystray.MenuItem("Trigger Scout Cycle", lambda icon, item: self.after(0, self._trigger_dream_mode)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Dione", lambda icon, item: self.on_quit_completely()),
        )
        self._tray_icon = pystray.Icon("Dione", _create_tray_image(), "Dione AI — Sovereign Personal Assistant", menu=menu)
        threading.Thread(target=self._tray_icon.run, daemon=True, name="DioneNativeTray").start()

    def on_minimize_to_tray(self):
        self.withdraw()

    def on_restore_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_quit_completely(self):
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self.destroy()
        os._exit(0)


if __name__ == "__main__":
    app = DioneNativeApp()
    app.mainloop()
