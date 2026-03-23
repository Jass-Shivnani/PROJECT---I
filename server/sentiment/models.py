"""
Dione AI — Sentiment Data Models

Defines the data structures for sentiment analysis results.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SentimentLabel(Enum):
    """High-level sentiment categories."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class EmotionLabel(Enum):
    """Fine-grained emotion categories."""
    JOY = "joy"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    SURPRISE = "surprise"
    FEAR = "fear"
    SADNESS = "sadness"
    ANGER = "anger"
    DISGUST = "disgust"
    NEUTRAL = "neutral"


class UrgencyLevel(Enum):
    """How urgently does this message need attention?"""
    CRITICAL = "critical"     # Needs immediate action
    HIGH = "high"             # Should be addressed soon
    MEDIUM = "medium"         # Normal priority
    LOW = "low"               # Can be batched / dealt with later
    INFORMATIONAL = "info"    # FYI only, no action needed


@dataclass
class SentimentResult:
    """Complete sentiment analysis result for a message."""
    
    # Core sentiment
    label: SentimentLabel
    confidence: float        # 0.0 to 1.0
    
    # Emotional tone
    emotion: EmotionLabel
    emotion_confidence: float
    
    # Urgency scoring (Dione's key differentiator)
    urgency: float           # 0.0 to 1.0
    urgency_level: UrgencyLevel
    
    # Importance scoring
    importance: float        # 0.0 to 1.0 (how relevant to user's goals)
    
    # Action suggestions
    suggested_priority: str  # "immediate", "soon", "batch", "ignore"
    
    # Raw scores
    raw_scores: Optional[dict] = None

    def __str__(self) -> str:
        return (
            f"Sentiment({self.label.value}, urgency={self.urgency:.2f}, "
            f"emotion={self.emotion.value}, importance={self.importance:.2f})"
        )

    def should_notify_immediately(self) -> bool:
        """Should this message trigger an immediate push notification?"""
        return (
            self.urgency_level in (UrgencyLevel.CRITICAL, UrgencyLevel.HIGH)
            or self.urgency > 0.7
        )

    def should_batch(self) -> bool:
        """Should this message be batched into a daily summary?"""
        return (
            self.urgency_level in (UrgencyLevel.LOW, UrgencyLevel.INFORMATIONAL)
            and self.importance < 0.4
        )
