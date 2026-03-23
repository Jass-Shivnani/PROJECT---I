"""
Dione AI — Sentiment Analyzer

STAR FACTOR #2: Deep sentiment analysis on every message.

Unlike simple positive/negative classification, Dione's sentiment
engine scores messages on three axes:
1. Emotion (joy, anger, fear, etc.)
2. Urgency (how quickly does this need a response?)
3. Importance (how relevant is this to the user's goals?)

This allows Dione to dynamically prioritize notifications,
suggest response urgency, and adapt its behavior based on
the emotional context of the conversation.
"""

import re
from typing import Optional
from loguru import logger

from server.sentiment.models import (
    SentimentResult,
    SentimentLabel,
    EmotionLabel,
    UrgencyLevel,
)


class SentimentAnalyzer:
    """
    Multi-dimensional sentiment analysis engine.
    
    Supports two modes:
    - "local": Rule-based + lightweight model (fast, no GPU needed)
    - "llm": Uses the local LLM for deeper analysis (slower, more accurate)
    """

    def __init__(self, mode: str = "local"):
        self.mode = mode
        self._transformer_model = None
        self._initialized = False

    async def initialize(self):
        """Load sentiment analysis models."""
        if self.mode == "local":
            try:
                from transformers import pipeline
                self._transformer_model = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english",
                    device=-1,  # CPU
                )
                self._initialized = True
                logger.info("Sentiment analyzer initialized (local transformer)")
            except Exception as e:
                logger.warning(f"Transformer model unavailable, using rule-based: {e}")
                self._initialized = True  # Fall back to rules
        else:
            self._initialized = True
            logger.info("Sentiment analyzer initialized (LLM mode)")

    async def analyze(self, text: str) -> SentimentResult:
        """
        Analyze the sentiment, emotion, and urgency of a text.
        
        Returns a comprehensive SentimentResult with scores across
        all three axes.
        """
        if not self._initialized:
            await self.initialize()

        # Step 1: Basic sentiment (positive/negative/neutral)
        base_sentiment = await self._analyze_base_sentiment(text)

        # Step 2: Emotion detection
        emotion, emotion_conf = self._detect_emotion(text)

        # Step 3: Urgency scoring
        urgency = self._score_urgency(text)
        urgency_level = self._urgency_to_level(urgency)

        # Step 4: Importance scoring
        importance = self._score_importance(text)

        # Step 5: Determine suggested priority
        priority = self._compute_priority(urgency, importance, emotion)

        return SentimentResult(
            label=base_sentiment["label"],
            confidence=base_sentiment["confidence"],
            emotion=emotion,
            emotion_confidence=emotion_conf,
            urgency=urgency,
            urgency_level=urgency_level,
            importance=importance,
            suggested_priority=priority,
            raw_scores=base_sentiment.get("raw", {}),
        )

    # ------------------------------------------------------------------
    # Base sentiment analysis
    # ------------------------------------------------------------------

    async def _analyze_base_sentiment(self, text: str) -> dict:
        """Get base positive/negative/neutral sentiment."""
        if self._transformer_model:
            try:
                result = self._transformer_model(text[:512])  # Truncate for model
                label_map = {
                    "POSITIVE": SentimentLabel.POSITIVE,
                    "NEGATIVE": SentimentLabel.NEGATIVE,
                }
                return {
                    "label": label_map.get(result[0]["label"], SentimentLabel.NEUTRAL),
                    "confidence": result[0]["score"],
                    "raw": result[0],
                }
            except Exception as e:
                logger.debug(f"Transformer failed, using rules: {e}")

        # Rule-based fallback
        return self._rule_based_sentiment(text)

    def _rule_based_sentiment(self, text: str) -> dict:
        """Simple rule-based sentiment as fallback."""
        text_lower = text.lower()

        positive_words = {
            "great", "awesome", "excellent", "good", "happy", "love",
            "wonderful", "fantastic", "perfect", "amazing", "thanks",
            "appreciate", "glad", "pleased", "excited", "congratulations",
        }
        negative_words = {
            "bad", "terrible", "awful", "horrible", "angry", "frustrated",
            "disappointed", "hate", "worse", "worst", "urgent", "asap",
            "problem", "issue", "error", "fail", "broken", "wrong",
            "annoyed", "upset", "worried", "concerned", "critical",
        }

        words = set(re.findall(r'\w+', text_lower))
        pos_count = len(words & positive_words)
        neg_count = len(words & negative_words)

        if pos_count > neg_count:
            return {"label": SentimentLabel.POSITIVE, "confidence": 0.6}
        elif neg_count > pos_count:
            return {"label": SentimentLabel.NEGATIVE, "confidence": 0.6}
        else:
            return {"label": SentimentLabel.NEUTRAL, "confidence": 0.5}

    # ------------------------------------------------------------------
    # Emotion detection
    # ------------------------------------------------------------------

    def _detect_emotion(self, text: str) -> tuple[EmotionLabel, float]:
        """Detect the primary emotion in the text."""
        text_lower = text.lower()

        emotion_keywords = {
            EmotionLabel.JOY: ["happy", "excited", "glad", "great", "love", "wonderful", "celebrate"],
            EmotionLabel.ANGER: ["angry", "furious", "annoyed", "frustrated", "outraged", "mad"],
            EmotionLabel.FEAR: ["worried", "scared", "afraid", "anxious", "nervous", "concerned"],
            EmotionLabel.SADNESS: ["sad", "disappointed", "sorry", "unfortunately", "regret", "miss"],
            EmotionLabel.SURPRISE: ["wow", "unexpected", "surprising", "shocked", "incredible", "unbelievable"],
            EmotionLabel.TRUST: ["trust", "reliable", "confident", "sure", "certain", "depend"],
            EmotionLabel.ANTICIPATION: ["looking forward", "can't wait", "eager", "upcoming", "soon"],
            EmotionLabel.DISGUST: ["disgusting", "gross", "terrible", "unacceptable", "revolting"],
        }

        scores = {}
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[emotion] = score

        if scores:
            best_emotion = max(scores, key=scores.get)
            confidence = min(scores[best_emotion] / 3.0, 1.0)
            return best_emotion, confidence

        return EmotionLabel.NEUTRAL, 0.5

    # ------------------------------------------------------------------
    # Urgency scoring
    # ------------------------------------------------------------------

    def _score_urgency(self, text: str) -> float:
        """
        Score the urgency of a message from 0.0 (not urgent) to 1.0 (critical).
        
        Considers:
        - Urgency keywords (ASAP, urgent, immediately)
        - Exclamation marks and caps
        - Time-sensitive language
        - Question marks (questions need responses)
        """
        text_lower = text.lower()
        score = 0.0

        # Urgency keywords (weighted)
        urgency_patterns = {
            0.9: ["asap", "urgent", "emergency", "critical", "immediately", "right now"],
            0.7: ["deadline", "today", "tonight", "within the hour", "time-sensitive"],
            0.5: ["soon", "important", "priority", "please respond", "need your help"],
            0.3: ["when you can", "no rush", "at your convenience", "fyi"],
        }

        for weight, patterns in urgency_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    score = max(score, weight)

        # Caps lock = shouting = urgency
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.5 and len(text) > 10:
            score = max(score, 0.6)

        # Multiple exclamation marks
        if text.count("!") >= 3:
            score = max(score, 0.5)

        # Question marks suggest expecting a response
        if "?" in text:
            score = max(score, 0.3)

        return min(score, 1.0)

    def _urgency_to_level(self, urgency: float) -> UrgencyLevel:
        """Convert urgency score to a level."""
        if urgency >= 0.8:
            return UrgencyLevel.CRITICAL
        elif urgency >= 0.6:
            return UrgencyLevel.HIGH
        elif urgency >= 0.4:
            return UrgencyLevel.MEDIUM
        elif urgency >= 0.2:
            return UrgencyLevel.LOW
        else:
            return UrgencyLevel.INFORMATIONAL

    # ------------------------------------------------------------------
    # Importance scoring
    # ------------------------------------------------------------------

    def _score_importance(self, text: str) -> float:
        """
        Score how important a message is to the user.
        
        Considers:
        - Mentions of key entities (people, projects)
        - Financial/legal language
        - Action items
        - Message length (longer = likely more important)
        """
        text_lower = text.lower()
        score = 0.3  # Base importance

        # Financial/legal significance
        important_domains = [
            "payment", "invoice", "salary", "contract", "deadline",
            "meeting", "interview", "presentation", "exam", "submission",
            "doctor", "appointment", "flight", "booking", "reservation",
        ]
        for domain in important_domains:
            if domain in text_lower:
                score += 0.15

        # Action items
        action_patterns = [
            "please", "need you to", "can you", "should", "must",
            "have to", "required", "assigned", "review", "approve",
        ]
        for pattern in action_patterns:
            if pattern in text_lower:
                score += 0.1

        # Longer messages tend to be more substantive
        if len(text) > 200:
            score += 0.1
        elif len(text) > 500:
            score += 0.2

        return min(score, 1.0)

    # ------------------------------------------------------------------
    # Priority computation
    # ------------------------------------------------------------------

    def _compute_priority(
        self, urgency: float, importance: float, emotion: EmotionLabel
    ) -> str:
        """Compute the suggested action priority."""
        # Anger/fear + high urgency = immediate
        emotional_boost = 0.0
        if emotion in (EmotionLabel.ANGER, EmotionLabel.FEAR):
            emotional_boost = 0.2

        combined = (urgency * 0.5 + importance * 0.3 + emotional_boost * 0.2)

        if combined >= 0.7:
            return "immediate"
        elif combined >= 0.5:
            return "soon"
        elif combined >= 0.3:
            return "batch"
        else:
            return "ignore"
