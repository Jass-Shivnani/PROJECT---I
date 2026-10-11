"""
Dione Next-Gen — Context-Aware Spoken Filler & Bridge Engine

Generates human-like conversational bridging phrases on the fly:
"Hmm, let me thinkkkk...", "Ummm hold on a sec, looking through your files...",
"Aha, got it! Here's what I found..."

Provides instantaneous conversational acknowledgment (<200ms) while
background cognitive reasoning and computer-use subagents execute.
"""

import random
import re
from typing import Dict, List, Optional
from loguru import logger


class SpokenFillerEngine:
    """
    Intelligent verbal bridge generator that prevents dead-air silence.
    Maps user prompts to natural conversational thoughts and milestones.
    """

    # Domain specific initial bridges
    DOMAIN_BRIDGES: Dict[str, List[str]] = {
        "whatsapp": [
            "Hmm, let me check your WhatsApp messages... hold on a sec...",
            "Ummm, opening up your chats right now... let's see...",
            "Checking WhatsApp for you... gimme a quick moment...",
        ],
        "email": [
            "Hmm, let me dig into your emails... one second...",
            "Checking your inbox right now... let me see what's there...",
            "Ummm, pulling up your latest emails... hold on...",
        ],
        "file": [
            "Hmm, let me search your files for that... scanning now...",
            "Ummm, looking through your documents... let's see...",
            "Searching your drive for that right now... hold on a sec...",
        ],
        "spotify_media": [
            "Ummm, opening Spotify to get that playing for you... one sec...",
            "Hmm, tuning into that music... let me set it up...",
            "Got it, handling Spotify for you right now...",
        ],
        "system_desktop": [
            "Hmm, let me check your system settings... one second...",
            "Ummm, taking a look at your desktop right now...",
            "Working on that on your PC... hold on a moment...",
        ],
        "knowledge_graph": [
            "Hmm, let me check your personal knowledge graph... searching your notes...",
            "Ummm, checking what you noted about that... let's see...",
            "Looking up your connections and commitments... one second...",
        ],
        "general_reasoning": [
            "Hmm, let me think about that for a second... let's see...",
            "Ummm, working through that right now... hold on...",
            "Let me analyze that for you... thinking...",
            "Hmm, good question... let me piece that together...",
        ],
    }

    # Intermediate milestone interjections (if background work takes >3 seconds)
    PROGRESS_INTERJECTIONS: List[str] = [
        "Still working on it, almost there...",
        "Just pulling the final details together...",
        "Connecting the pieces right now...",
        "Just a second longer, verifying that...",
    ]

    # Triumph / completion bridges
    RESOLUTION_BRIDGES: List[str] = [
        "Aha, got it!",
        "Uhhh yeah, found it!",
        "Alright, got it!",
        "Aha, here's what I found!",
        "Done, take a look!",
    ]

    def __init__(self):
        self._last_bridge: Optional[str] = None

    def detect_domain(self, text: str) -> str:
        """Rapid regex heuristic to classify intent for contextual filler."""
        t = text.lower()

        if re.search(r"\b(promises?|commitments?|remember|who is|relations?|friends?|dossier)\b", t):
            return "knowledge_graph"
        if re.search(r"\b(whatsapp|chat|text message|alice|riya|khushi|ruchika)\b", t):
            return "whatsapp"
        if re.search(r"\b(email|gmail|inbox|mail|send email)\b", t):
            return "email"
        if re.search(r"\b(file|folder|document|pdf|docx|download|drive|black book|report)\b", t):
            return "file"
        if re.search(r"\b(spotify|music|song|playlist|play|pause|volume|track)\b", t):
            return "spotify_media"
        if re.search(r"\b(app|window|screen|pc|screenshot|mouse|click|ram|cpu|process|battery)\b", t):
            return "system_desktop"

        return "general_reasoning"

    def get_opening_bridge(self, user_prompt: str) -> str:
        """Select an expressive, natural opening spoken thought."""
        domain = self.detect_domain(user_prompt)
        candidates = self.DOMAIN_BRIDGES.get(domain, self.DOMAIN_BRIDGES["general_reasoning"])

        # Avoid repeating the immediate previous bridge
        filtered = [c for c in candidates if c != self._last_bridge]
        choice = random.choice(filtered) if filtered else random.choice(candidates)
        self._last_bridge = choice
        logger.debug(f"[FillerEngine] Domain: '{domain}' -> Spoken Bridge: '{choice}'")
        return choice

    def get_progress_bridge(self) -> str:
        """Emit an intermediate thought if agent needs more time."""
        return random.choice(self.PROGRESS_INTERJECTIONS)

    def get_resolution_bridge(self) -> str:
        """Emit the victorious handoff phrase before reading results."""
        return random.choice(self.RESOLUTION_BRIDGES)


# Global singleton
_filler_engine: Optional[SpokenFillerEngine] = None


def get_filler_engine() -> SpokenFillerEngine:
    global _filler_engine
    if _filler_engine is None:
        _filler_engine = SpokenFillerEngine()
    return _filler_engine
