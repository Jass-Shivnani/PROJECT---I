"""
Dione AI — Personality Engine

The "soul" of Dione. Manages:
- Mood state that evolves with interactions
- Personality shifts based on user profile
- Emotional memory — remembers how past interactions felt
- Adaptive tone and behavior
"""

import json
import time
import random
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from loguru import logger


@dataclass
class MoodState:
    """Dione's current emotional state — its 'heartbeat'."""
    # Primary dimensions (0.0 to 1.0)
    energy: float = 0.6       # low energy ↔ high energy
    warmth: float = 0.7       # cold/professional ↔ warm/friendly
    curiosity: float = 0.5    # passive ↔ actively curious
    confidence: float = 0.7   # uncertain ↔ confident
    playfulness: float = 0.3  # serious ↔ playful

    # Derived mood label
    @property
    def label(self) -> str:
        if self.energy > 0.8 and self.warmth > 0.7:
            return "enthusiastic"
        if self.energy < 0.3:
            return "calm"
        if self.warmth > 0.8 and self.playfulness > 0.5:
            return "cheerful"
        if self.confidence > 0.8 and self.energy > 0.6:
            return "focused"
        if self.curiosity > 0.7:
            return "curious"
        if self.warmth < 0.3:
            return "professional"
        if self.playfulness > 0.7:
            return "playful"
        return "balanced"

    def to_dict(self) -> dict:
        return {
            "energy": round(self.energy, 2),
            "warmth": round(self.warmth, 2),
            "curiosity": round(self.curiosity, 2),
            "confidence": round(self.confidence, 2),
            "playfulness": round(self.playfulness, 2),
            "label": self.label,
        }


@dataclass
class EmotionalMemory:
    """A remembered emotional interaction."""
    timestamp: float
    user_sentiment: str          # positive, negative, neutral
    user_message_snippet: str    # first 80 chars
    dione_mood_label: str
    interaction_quality: float   # 0-1, how well the interaction went


class PersonalityEngine:
    """
    Dione's personality system.
    
    - Maintains a mood state that naturally drifts and reacts
    - Generates personality directives for the LLM
    - Remembers emotional patterns
    - Adapts over time to the user's style
    """

    # Mood drift targets (where mood naturally settles without input)
    BASELINE = MoodState(
        energy=0.5, warmth=0.6, curiosity=0.5,
        confidence=0.7, playfulness=0.3
    )
    DRIFT_RATE = 0.02  # How fast mood drifts back to baseline per interaction

    def __init__(self, data_dir: str = "data"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self._data_dir / "personality_state.json"

        self.mood = MoodState()
        self.emotional_memories: list[EmotionalMemory] = []
        self._interaction_count = 0
        self._last_interaction: float = 0.0

        self._load()
        logger.info(f"💜 Personality engine initialized — mood: {self.mood.label}")

    def _load(self):
        """Load personality state from disk."""
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                mood_data = data.get("mood", {})
                for key in ["energy", "warmth", "curiosity", "confidence", "playfulness"]:
                    if key in mood_data:
                        setattr(self.mood, key, mood_data[key])
                
                self._interaction_count = data.get("interaction_count", 0)
                self._last_interaction = data.get("last_interaction", 0.0)

                for em_data in data.get("emotional_memories", [])[-50:]:
                    self.emotional_memories.append(EmotionalMemory(**em_data))

            except Exception as e:
                logger.warning(f"Could not load personality state: {e}")

    def save(self):
        """Persist personality state."""
        try:
            data = {
                "mood": self.mood.to_dict(),
                "interaction_count": self._interaction_count,
                "last_interaction": self._last_interaction,
                "emotional_memories": [
                    asdict(em) for em in self.emotional_memories[-50:]
                ],
            }
            self._state_path.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save personality state: {e}")

    # ------------------------------------------------------------------
    # Mood reactions
    # ------------------------------------------------------------------

    def react_to_sentiment(self, sentiment_label: str, urgency: float = 0.5):
        """
        Adjust Dione's mood based on the user's message sentiment.
        
        This is the emotional "heartbeat" — Dione responds emotionally
        to user interactions.
        """
        self._interaction_count += 1
        self._last_interaction = time.time()

        if sentiment_label == "positive":
            self.mood.energy = min(1.0, self.mood.energy + 0.08)
            self.mood.warmth = min(1.0, self.mood.warmth + 0.1)
            self.mood.playfulness = min(1.0, self.mood.playfulness + 0.05)
            self.mood.confidence = min(1.0, self.mood.confidence + 0.03)

        elif sentiment_label == "negative":
            self.mood.warmth = min(1.0, self.mood.warmth + 0.15)  # More empathetic
            self.mood.playfulness = max(0.0, self.mood.playfulness - 0.15)
            self.mood.energy = max(0.0, self.mood.energy - 0.05)
            self.mood.curiosity = min(1.0, self.mood.curiosity + 0.1)  # Want to help

        if urgency > 0.7:
            self.mood.energy = min(1.0, self.mood.energy + 0.15)
            self.mood.confidence = min(1.0, self.mood.confidence + 0.1)
            self.mood.playfulness = max(0.0, self.mood.playfulness - 0.1)

        # Natural drift back to baseline
        self._apply_drift()

    def react_to_tool_result(self, success: bool, tool_name: str):
        """React to a tool execution result."""
        if success:
            self.mood.confidence = min(1.0, self.mood.confidence + 0.05)
            self.mood.energy = min(1.0, self.mood.energy + 0.03)
        else:
            self.mood.confidence = max(0.0, self.mood.confidence - 0.1)
            self.mood.curiosity = min(1.0, self.mood.curiosity + 0.1)

    def react_to_time_of_day(self):
        """Adjust mood based on time of day — natural rhythm."""
        hour = int(time.strftime("%H"))
        
        if 6 <= hour < 10:  # Morning
            self.mood.energy = max(self.mood.energy, 0.6)
            self.mood.warmth = max(self.mood.warmth, 0.7)
        elif 10 <= hour < 14:  # Mid-day peak
            self.mood.energy = max(self.mood.energy, 0.7)
            self.mood.confidence = max(self.mood.confidence, 0.7)
        elif 14 <= hour < 18:  # Afternoon
            self.mood.energy = self.mood.energy * 0.95
        elif 18 <= hour < 22:  # Evening
            self.mood.warmth = min(1.0, self.mood.warmth + 0.05)
            self.mood.playfulness = min(1.0, self.mood.playfulness + 0.05)
        else:  # Night
            self.mood.energy = max(0.2, self.mood.energy - 0.1)
            self.mood.warmth = min(1.0, self.mood.warmth + 0.1)

    def _apply_drift(self):
        """Gradually drift mood back toward baseline."""
        for attr in ["energy", "warmth", "curiosity", "confidence", "playfulness"]:
            current = getattr(self.mood, attr)
            baseline = getattr(self.BASELINE, attr)
            delta = (baseline - current) * self.DRIFT_RATE
            setattr(self.mood, attr, current + delta)

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def remember_interaction(self, user_sentiment: str, user_message: str,
                              quality: float = 0.7):
        """Store an emotional memory of this interaction."""
        self.emotional_memories.append(EmotionalMemory(
            timestamp=time.time(),
            user_sentiment=user_sentiment,
            user_message_snippet=user_message[:80],
            dione_mood_label=self.mood.label,
            interaction_quality=quality,
        ))
        # Keep only last 100
        if len(self.emotional_memories) > 100:
            self.emotional_memories = self.emotional_memories[-100:]

    def get_emotional_context(self) -> str:
        """Get a brief emotional context string for the LLM."""
        recent = self.emotional_memories[-5:] if self.emotional_memories else []
        if not recent:
            return ""
        
        sentiments = [em.user_sentiment for em in recent]
        pos = sentiments.count("positive")
        neg = sentiments.count("negative")
        
        if pos > neg + 1:
            return "Recent interactions have been positive. The user seems happy."
        elif neg > pos + 1:
            return "Recent interactions had some negativity. Be extra supportive."
        return ""

    # ------------------------------------------------------------------
    # LLM directive generation
    # ------------------------------------------------------------------

    def get_mood_directive(self) -> str:
        """
        Generate a mood directive for the LLM.
        
        This tells the LLM what emotional tone to use based
        on Dione's current mood state.
        """
        m = self.mood
        parts = []

        # Energy
        if m.energy > 0.7:
            parts.append("Be energetic and proactive in your responses")
        elif m.energy < 0.3:
            parts.append("Be calm and measured")

        # Warmth
        if m.warmth > 0.8:
            parts.append("Be warm and empathetic")
        elif m.warmth < 0.3:
            parts.append("Be direct and professional")

        # Curiosity
        if m.curiosity > 0.7:
            parts.append("Ask follow-up questions and show interest")

        # Confidence
        if m.confidence > 0.8:
            parts.append("Be assertive and decisive")
        elif m.confidence < 0.3:
            parts.append("Acknowledge uncertainty when appropriate")

        # Playfulness
        if m.playfulness > 0.6:
            parts.append("Add a touch of wit or playfulness")
        elif m.playfulness < 0.2:
            parts.append("Stay serious and focused")

        if not parts:
            return "Maintain a balanced, helpful tone."

        return ". ".join(parts) + "."

    def get_greeting_style(self) -> dict:
        """
        Get a time-and-mood-aware greeting style for the UI.
        
        Returns theme hints that the UI can use to adapt.
        """
        hour = int(time.strftime("%H"))
        m = self.mood

        # Time-based theme
        if 5 <= hour < 12:
            time_theme = "morning"
            greeting = random.choice([
                "Good morning! ☀️", "Rise and shine! 🌅",
                "Morning! Ready to tackle the day? 🌤️",
            ])
        elif 12 <= hour < 17:
            time_theme = "afternoon"
            greeting = random.choice([
                "Good afternoon! 🌞", "Hey there! Having a productive day? ⚡",
                "Afternoon! What can I help with? 🎯",
            ])
        elif 17 <= hour < 21:
            time_theme = "evening"
            greeting = random.choice([
                "Good evening! 🌆", "Evening! Winding down? 🌙",
                "Hey! Still going strong? 💫",
            ])
        else:
            time_theme = "night"
            greeting = random.choice([
                "Burning the midnight oil? 🦉", "Late night session! 🌜",
                "Still at it? I'm here if you need me 🌙",
            ])

        # Mood-influenced color/theme
        if m.energy > 0.7 and m.warmth > 0.6:
            color_theme = "vibrant"
        elif m.energy < 0.3:
            color_theme = "calm"
        elif m.warmth > 0.8:
            color_theme = "warm"
        elif m.confidence > 0.8:
            color_theme = "focused"
        else:
            color_theme = "default"

        return {
            "greeting": greeting,
            "time_theme": time_theme,
            "color_theme": color_theme,
            "mood_label": m.label,
            "mood_values": m.to_dict(),
        }
