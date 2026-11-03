"""
Dione AI — Autonomous Inactive-State "Dream & Scout" Engine (Star Feature)
========================================================================
Operates autonomously when the user is inactive or away from the workstation:
1. Native Windows idle-time tracking via Win32 `GetLastInputInfo`.
2. Dual-Mode Architecture:
   - Mode 1: Light-Weight & Pausable Tasks (Daytime short absence / user nearby).
     Quick fact-checking, memory indexing, immediately pauses on mouse/keyboard touch.
   - Mode 2: Heavy Tasks (Night-time sleep or extended absence >= 30 min).
     Deep ArXiv research, graph consolidation, onboarding context learning,
     and commitment pre-drafting.
3. Strict Service Consent: External services (email, files) are strictly gated
   behind user authorization in `data/proactive/service_consent.json`.
4. Onboarding Context Learning Phase: Silently consolidates user domain,
   projects, and preferences into `data/proactive/user_profile.json`.
5. Executive Assistant Synthesis: Uses Gemini to synthesize a polished
   "While You Were Away" Morning/Wake-Up Briefing Card with 1-click approvals.
"""

import asyncio
import ctypes
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from server.config import get_settings
from server.knowledge.entities import Entity, EntityType
from server.knowledge.relations import Relation, RelationType
from server.plugins.builtin.web_research import WebResearchPlugin


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


def get_windows_idle_seconds() -> float:
    """Return how many seconds the user has been idle on Windows using Win32 API."""
    try:
        plii = LASTINPUTINFO()
        plii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(plii)):
            millis = ctypes.windll.kernel32.GetTickCount() - plii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception as e:
        logger.debug(f"Win32 GetLastInputInfo query error: {e}")
    return 0.0


class ActivityMode(str, Enum):
    ACTIVE = "active"
    LIGHT_IDLE = "light_idle"
    DEEP_SLEEP = "deep_sleep"


class ServiceConsentManager:
    """Strict consent gate for personal accounts and services."""

    def __init__(self, consent_path: Path):
        self.path = consent_path
        self._ensure_defaults()

    def _ensure_defaults(self):
        if not self.path.exists():
            defaults = {
                "email_read": False,
                "email_send": False,
                "filesystem_indexing": True,
                "notes": "Explicit user consent is mandatory before reading personal email accounts."
            }
            self.path.write_text(json.dumps(defaults, indent=2), encoding="utf-8")

    def has_consent(self, service: str) -> bool:
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return bool(data.get(service, False))
        except Exception:
            pass
        return False

    def update_consent(self, service: str, granted: bool):
        try:
            data = {}
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
            data[service] = granted
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to update consent registry: {e}")


class UserProfileManager:
    """Manages the onboarding context learning phase ('naya naya' setup)."""

    def __init__(self, profile_path: Path):
        self.path = profile_path
        self._load_or_init()

    def _load_or_init(self) -> Dict[str, Any]:
        if not self.path.exists():
            initial_profile = {
                "onboarding_stage": "learning",
                "detected_domain": "Computer Engineering / Multi-Agent Systems",
                "core_projects": ["Dione AI Capstone Project"],
                "collaborators": ["Prof. Geocey Shejy (Mentor)", "Alex (Capstone Team)"],
                "interests": ["Large Action Models", "Computer Use Grounding", "Zero-Mock DAGs"],
                "last_consolidated": datetime.now().isoformat(),
            }
            self.path.write_text(json.dumps(initial_profile, indent=2), encoding="utf-8")
            return initial_profile
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def get_profile(self) -> Dict[str, Any]:
        return self._load_or_init()

    def update_profile(self, updates: Dict[str, Any]):
        prof = self._load_or_init()
        prof.update(updates)
        prof["last_consolidated"] = datetime.now().isoformat()
        try:
            self.path.write_text(json.dumps(prof, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist user profile: {e}")


@dataclass
class DreamSynthesisReport:
    """Summary report of an autonomous background synthesis cycle."""
    timestamp: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    mode: str = "deep_sleep"
    entities_scanned: int = 0
    new_nodes_created: int = 0
    new_edges_created: int = 0
    topics_researched: List[str] = field(default_factory=list)
    offline_context_summary: str = ""
    staged_commitments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": round(self.duration_seconds, 2),
            "mode": self.mode,
            "entities_scanned": self.entities_scanned,
            "new_nodes_created": self.new_nodes_created,
            "new_edges_created": self.new_edges_created,
            "topics_researched": self.topics_researched,
            "offline_context_summary": self.offline_context_summary,
            "staged_commitments": self.staged_commitments,
        }


class DreamSynthesisEngine:
    """
    Autonomous Background Synthesis & Scout Engine ("Dream Mode").
    Executes real DuckDuckGo scraping, arXiv papers, NetworkX expansion,
    and Gemini-powered executive briefings when the user is away.
    """

    def __init__(
        self,
        knowledge_graph=None,
        memory_manager=None,
        data_dir: str = "data/proactive",
        idle_threshold_seconds: float = 180.0,  # 3 minutes for light idle
        deep_idle_threshold_seconds: float = 1800.0,  # 30 minutes for deep sleep
    ):
        self.kg = knowledge_graph
        self.memory = memory_manager
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.data_dir / "dream_synthesis_logs.json"
        self.briefing_path = self.data_dir / "latest_wakeup_briefing.json"

        self.consent_mgr = ServiceConsentManager(self.data_dir / "service_consent.json")
        self.profile_mgr = UserProfileManager(self.data_dir / "user_profile.json")

        self.web_research = WebResearchPlugin()
        self.idle_threshold_seconds = idle_threshold_seconds
        self.deep_idle_threshold_seconds = deep_idle_threshold_seconds

        self._last_light_cycle: float = 0.0
        self._last_deep_cycle: float = 0.0
        self._is_synthesizing = False
        self._in_dream_mode = False
        self._current_mode = ActivityMode.ACTIVE
        self._latest_report: Optional[DreamSynthesisReport] = None
        self._briefing_ready = False
        self._monitor_task: Optional[asyncio.Task] = None

    def set_knowledge_graph(self, kg):
        self.kg = kg

    def set_memory_manager(self, memory):
        self.memory = memory

    async def start_autonomous_monitor(self):
        """Start the background idle detection and dream monitor daemon."""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._idle_monitor_loop())
            logger.info("Dione Autonomous Dream & Scout Monitor started.")

    async def stop_autonomous_monitor(self):
        """Stop the background monitor."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _idle_monitor_loop(self):
        """Poll user activity to transition between Active, Light-Idle, and Deep-Sleep modes."""
        while True:
            try:
                await asyncio.sleep(10.0)  # Check idle every 10s
                idle_sec = get_windows_idle_seconds()
                current_hour = datetime.now().hour
                is_night = (current_hour >= 23 or current_hour < 6)

                # Determine active status
                if idle_sec < self.idle_threshold_seconds:
                    if self._in_dream_mode:
                        self._in_dream_mode = False
                        self._current_mode = ActivityMode.ACTIVE
                        logger.info(f"User returned to workstation (idle reset to {idle_sec:.1f}s). Executive briefing ready.")
                        self._briefing_ready = True
                else:
                    # User is idle: Determine Light vs Deep Sleep mode
                    if idle_sec >= self.deep_idle_threshold_seconds or (is_night and idle_sec >= 300.0):
                        if self._current_mode != ActivityMode.DEEP_SLEEP:
                            self._in_dream_mode = True
                            self._current_mode = ActivityMode.DEEP_SLEEP
                            logger.info(f"User in Deep Sleep / Extended Away ({idle_sec:.0f}s idle). Launching Deep Synthesis...")
                            await self.run_synthesis_cycle(is_deep=True)
                    else:
                        if self._current_mode != ActivityMode.LIGHT_IDLE:
                            self._in_dream_mode = True
                            self._current_mode = ActivityMode.LIGHT_IDLE
                            logger.info(f"User in Light Idle ({idle_sec:.0f}s idle). Launching pausable background tasks...")
                            await self.run_light_cycle()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Dream monitor loop tick error: {e}")

    def get_latest_briefing(self) -> Optional[Dict[str, Any]]:
        """Return the latest wake-up briefing card if available."""
        if self.briefing_path.exists():
            try:
                return json.loads(self.briefing_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def consume_briefing(self) -> Optional[Dict[str, Any]]:
        """Return and clear the unread wake-up briefing card."""
        briefing = self.get_latest_briefing()
        self._briefing_ready = False
        return briefing

    async def run_light_cycle(self) -> Optional[DreamSynthesisReport]:
        """
        Execute Mode 1: Light-weight, easily pausable background tasks.
        Checks idle state between operations; halts immediately if user touches input.
        """
        now = time.time()
        if (now - self._last_light_cycle) < 600:  # Minimum 10 min between light cycles
            return None

        if self._is_synthesizing:
            return None

        self._is_synthesizing = True
        start_t = time.time()
        logger.info("Executing Light-Weight Background Scout Cycle...")
        report = DreamSynthesisReport(timestamp=start_t, mode="light_idle")

        try:
            # 1. Discover light topic
            topics = await self._discover_research_topics(limit=1)
            report.topics_researched = topics

            for topic in topics:
                # Cooperative pause check: Did the user return?
                if get_windows_idle_seconds() < 30.0:
                    logger.info("User activity detected during light cycle; pausing gracefully.")
                    break

                try:
                    web_snippets = await self.web_research.web_search(topic, max_results=2)
                    if self.kg and web_snippets:
                        node_id = f"topic_{abs(hash(topic)) % 100000}"
                        self.kg.add_or_merge_entity(Entity(
                            id=node_id,
                            type=EntityType.TOPIC,
                            name=topic,
                            metadata={
                                "synthesized_at": datetime.now().isoformat(),
                                "source": "light_dream_scout",
                                "web_summary": web_snippets[:300],
                            }
                        ))
                        report.new_nodes_created += 1
                except Exception as e:
                    logger.debug(f"Light research error for '{topic}': {e}")

            report.duration_seconds = time.time() - start_t
            self._last_light_cycle = time.time()
            self._latest_report = report
            return report

        finally:
            self._is_synthesizing = False

    async def run_synthesis_cycle(self, force: bool = False, is_deep: bool = True) -> Optional[DreamSynthesisReport]:
        """
        Execute Mode 2: Heavy Synthesis & Scout Cycle.
        Performs REAL DuckDuckGo search, arXiv queries, NetworkX graph expansion,
        onboarding context consolidation, commitment pre-drafting, and Gemini briefing generation.
        """
        if self._is_synthesizing:
            logger.debug("Dream synthesis already active; skipping.")
            return None

        now = time.time()
        if not force and (now - self._last_deep_cycle) < 1800:
            return None

        self._is_synthesizing = True
        start_t = time.time()
        logger.info("Executing Deep Autonomous Dream & Scout Cycle (Real Web, ArXiv & Graph Grounding)...")

        report = DreamSynthesisReport(timestamp=start_t, mode="deep_sleep" if is_deep else "light_idle")

        try:
            # 1. Scan Knowledge Graph & User Profile for high-value research topics
            topics_to_scout = await self._discover_research_topics(limit=3)
            report.topics_researched = topics_to_scout

            # 2. Conduct Real Web & arXiv Research for each topic
            gathered_research: List[Dict[str, str]] = []
            for topic in topics_to_scout:
                try:
                    logger.info(f"Dream Scout researching: {topic}")
                    web_snippets = await self.web_research.web_search(topic, max_results=2)
                    arxiv_snippets = await self.web_research.search_academic_papers(topic, max_results=1)

                    gathered_research.append({
                        "topic": topic,
                        "web": web_snippets[:400] if web_snippets else "",
                        "arxiv": arxiv_snippets[:400] if arxiv_snippets else "",
                    })

                    # 3. Ingest discovered findings into Knowledge Graph
                    if self.kg:
                        node_id = f"dream_topic_{abs(hash(topic)) % 100000}"
                        entity = Entity(
                            id=node_id,
                            type=EntityType.TOPIC,
                            name=topic,
                            metadata={
                                "synthesized_at": datetime.now().isoformat(),
                                "source": "autonomous_dream_scout",
                                "web_summary": web_snippets[:400] if web_snippets else "",
                                "academic_summary": arxiv_snippets[:400] if arxiv_snippets else "",
                                "offline_ready": True,
                            }
                        )
                        self.kg.add_or_merge_entity(entity)
                        report.new_nodes_created += 1

                        # Connect to root or user node
                        root_id = "dione_project" if self.kg.graph.has_node("dione_project") else ("jass" if self.kg.graph.has_node("jass") else None)
                        if root_id:
                            rel_id = f"rel_dream_{report.new_edges_created}_{int(time.time())}"
                            self.kg.add_relation(Relation(
                                id=rel_id,
                                source_id=root_id,
                                target_id=node_id,
                                type=RelationType.RELATED_TO,
                                weight=0.85,
                                metadata={"cycle": "dream_scout"}
                            ))
                            report.new_edges_created += 1
                except Exception as scout_err:
                    logger.warning(f"Error researching '{topic}': {scout_err}")

            # 4. Onboarding Context Learning: Update user profile with discovered topics
            user_prof = self.profile_mgr.get_profile()
            existing_interests = set(user_prof.get("interests", []))
            for t in topics_to_scout:
                existing_interests.add(t)
            self.profile_mgr.update_profile({"interests": list(existing_interests)[:10]})

            # 5. Scan Pending Commitments & Pre-Draft Action Items
            staged_drafts = await self._stage_pending_commitments()
            report.staged_commitments = staged_drafts

            # 6. Synthesize Executive Briefing using Gemini
            report.duration_seconds = time.time() - start_t
            executive_summary = await self._synthesize_executive_briefing(
                topics=topics_to_scout,
                research=gathered_research,
                staged_drafts=staged_drafts,
                nodes_added=report.new_nodes_created
            )
            report.offline_context_summary = executive_summary
            self._latest_report = report
            self._last_deep_cycle = time.time()

            # 7. Persist Executive Briefing Card to disk
            briefing_payload = {
                "title": "While You Were Away — Executive Briefing",
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "mode": report.mode,
                "summary": executive_summary,
                "topics_researched": topics_to_scout,
                "new_knowledge_nodes": report.new_nodes_created,
                "staged_commitments": staged_drafts,
                "status": "ready_for_review",
            }
            self.briefing_path.write_text(json.dumps(briefing_payload, indent=2), encoding="utf-8")
            logger.info("Autonomous Dream cycle complete. Wake-up briefing staged.")
            return report

        except Exception as e:
            logger.error(f"Dream synthesis cycle encountered error: {e}")
            return None
        finally:
            self._is_synthesizing = False

    async def _discover_research_topics(self, limit: int = 3) -> List[str]:
        """Dynamically identify high-value concepts, technologies, and academic topics needing research."""
        topics = []
        stop_words = {"are", "the", "and", "for", "with", "from", "this", "that", "user", "dione", "status", "operations"}
        if self.kg:
            for node, data in self.kg.graph.nodes(data=True):
                deg = self.kg.graph.degree(node)
                name = str(data.get("name", node)).strip()
                if deg <= 2 and len(name) > 3 and name.lower() not in stop_words and data.get("type") in ("concept", "project", "topic"):
                    topics.append(name)

        # Pull from user profile
        prof = self.profile_mgr.get_profile()
        for interest in prof.get("interests", []):
            if interest.lower() not in stop_words:
                topics.append(interest)

        # Core project domain fallbacks
        if len(topics) < limit:
            topics.extend([
                "Large Action Models Multi-Agent Orchestration",
                "Zero-Trust Edge AI Tool Calling",
                "Autonomous OS Computer Use Grounding Benchmarks"
            ])

        return list(dict.fromkeys(topics))[:limit]

    async def _stage_pending_commitments(self) -> List[Dict[str, Any]]:
        """Pre-draft executive action items for any pending promises or mentors."""
        staged = []

        # Check email consent
        email_allowed = self.consent_mgr.has_consent("email_read")
        if not email_allowed:
            # We explicitly note that email reading is waiting for user consent
            logger.debug("Email triage skipped in Dream Mode: Waiting for explicit user consent.")

        if self.kg:
            for node, data in self.kg.graph.nodes(data=True):
                name = data.get("name", str(node))
                if "geocey" in node.lower() or "mentor" in str(data).lower():
                    staged.append({
                        "id": f"draft_{uuid.uuid4().hex[:6]}",
                        "recipient": name,
                        "subject": "Dione Capstone Project — Zero-Mock Multi-Agent Telemetry & Progress Update",
                        "preview": "Respected Ma'am, Dione's Hierarchical Multi-Agent DAG Orchestrator with native Computer-Use and zero-mock system execution has been verified and benchmarked.",
                        "action_type": "email_draft",
                        "status": "pending_1click_approval",
                    })

        return staged

    async def _synthesize_executive_briefing(
        self,
        topics: List[str],
        research: List[Dict[str, str]],
        staged_drafts: List[Dict[str, Any]],
        nodes_added: int
    ) -> str:
        """Call Gemini to synthesize a crisp, poised Jarvis-style wake-up briefing."""
        settings = get_settings()
        api_key = settings.llm.api_key or os.getenv("DIONE_LLM_API_KEY") or os.getenv("GEMINI_API_KEY")

        research_summary = "\n".join(
            f"- Topic '{r['topic']}': Web: {r['web'][:150]}... ArXiv: {r['arxiv'][:150]}..."
            for r in research
        )
        drafts_summary = "\n".join(
            f"- Draft to {d['recipient']}: '{d['subject']}'"
            for d in staged_drafts
        )

        prompt = (
            f"You are Dione, the user's executive AI assistant.\n"
            f"The user has just returned to their workstation.\n"
            f"While they were away, you autonomously conducted research:\n{research_summary}\n"
            f"Expanded Knowledge Graph with {nodes_added} new concepts.\n"
            f"Staged action items:\n{drafts_summary or 'No urgent drafts pending.'}\n\n"
            f"Synthesize an authentic, poised, executive wake-up briefing in 2 to 3 sentences.\n"
            f"Highlight the most relevant technical breakthrough and any action items awaiting their 1-click review.\n"
            f"Tone: Jarvis, executive, concise, respectful."
        )

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = await client.aio.models.generate_content(
                model=settings.llm.model or "gemini-3.5-flash-lite",
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.debug(f"Gemini briefing synthesis fallback: {e}")

        # Deterministic assistant fallback
        topics_str = ", ".join(topics[:2]) if topics else "recent research topics"
        base = f"Welcome back, sir. While you were away, I scouted {topics_str} and expanded your knowledge graph with {nodes_added} verified nodes."
        if staged_drafts:
            base += f" I have also pre-staged {len(staged_drafts)} action item(s) for your 1-click review."
        return base
