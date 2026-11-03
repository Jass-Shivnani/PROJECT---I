"""
Dione 2026 — Cognitive Planner & Multi-Agent Runtime Bridge
============================================================
Bridges the Voice Frontman and TaskManager with the Hierarchical
Multi-Agent Orchestrator (`MultiAgentOrchestrator`) and `ComputerUseOperator`.
"""

import asyncio
from typing import Any, Dict, List, Optional
from loguru import logger

from server.core.runtime.event_bus import (
    AgentState,
    AsyncEventBus,
    EventType,
    RuntimeEvent,
    get_event_bus,
)
from server.core.runtime.computer_use import ComputerUseOperator, get_computer_use_operator
from server.core.orchestrator import get_multi_agent_orchestrator, OrchestrationSession


class CognitivePlanner:
    """
    Coordinates Multi-Agent DAG execution across:
    - SupervisorOrchestrator (Meta-Planner & Blackboard)
    - SafetyKernelAuditor (5-Tier Lattice & Injection Defense)
    - ComputerUseVisionAgent (Windows 11 UIA, GDI Screen Capture, Vision Click, Audio/App Control)
    - KnowledgeSocialAgent (NetworkX GraphRAG, Social Dossiers, Commitment Mining)
    - SystemSandboxAgent (Filesystem, SQLite DB, Hardware Telemetry)
    - ResearchWebAgent (Live Web & arXiv Search)
    """

    def __init__(
        self,
        event_bus: Optional[AsyncEventBus] = None,
        computer_use: Optional[ComputerUseOperator] = None,
        llm_adapter=None,
    ):
        self.bus = event_bus or get_event_bus()
        self.computer_use = computer_use or get_computer_use_operator()
        self.orchestrator = get_multi_agent_orchestrator()
        self.llm = llm_adapter
        self.last_session: Optional[OrchestrationSession] = None

    async def execute_goal(self, goal: str) -> str:
        """
        Execute an autonomous user goal end-to-end through the Multi-Agent Orchestrator DAG.
        """
        self.bus.set_state(AgentState.THINKING, reason=f"Orchestrating: {goal[:50]}")
        logger.info(f"[CognitivePlanner] 🧠 Orchestrating multi-agent DAG for: '{goal}'")

        await self.bus.publish(
            RuntimeEvent(
                event_type=EventType.GOAL_RECEIVED,
                payload={"goal": goal},
                sender="supervisor_orchestrator",
            )
        )

        session = await self.orchestrator.execute_orchestrated_goal(goal)
        self.last_session = session

        if self.llm and session.status != "blocked":
            try:
                enriched = (
                    f"User Goal: {goal}\n"
                    f"Multi-Agent Execution Summary:\n{session.final_synthesis}\n"
                    "Respond concisely and naturally."
                )
                response = await self.llm.generate(enriched)
                if response:
                    return response
            except Exception as e:
                logger.debug(f"[CognitivePlanner] LLM synthesis fallback: {e}")

        return session.final_synthesis


_cognitive_planner: Optional[CognitivePlanner] = None


def get_cognitive_planner() -> CognitivePlanner:
    global _cognitive_planner
    if _cognitive_planner is None:
        _cognitive_planner = CognitivePlanner()
    return _cognitive_planner
