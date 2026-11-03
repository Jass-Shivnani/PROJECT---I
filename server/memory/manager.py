"""
Dione AI — Memory Manager

The central memory system that combines:
1. Short-term: Recent conversation turns (sliding window)
2. Long-term: Embedded conversation chunks (ChromaDB)
3. Episodic: Significant events and milestones
4. Semantic: Knowledge graph entities and relations

This is what makes Dione feel ALIVE — she remembers your
birthday, your project deadlines, that you were stressed
last Tuesday, and that you prefer coffee over tea.
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Any, Union
from pathlib import Path

from loguru import logger

from server.memory.vectorstore import VectorStore
from server.memory.embeddings import EmbeddingService


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    id: str
    role: str            # "user" or "assistant"
    content: str
    timestamp: float
    sentiment: Optional[dict] = None
    metadata: Optional[dict] = None


@dataclass
class Episode:
    """A significant event worth remembering permanently."""
    id: str
    title: str
    description: str
    timestamp: float
    category: str        # "milestone", "preference", "relationship", "task"
    importance: float    # 0.0 to 1.0
    metadata: dict = field(default_factory=dict)


class MemoryManager:
    """
    Dione's memory system.
    
    Manages conversation history, long-term memory storage,
    and intelligent retrieval for context enrichment.
    """

    def __init__(
        self,
        data_dir: Any = "data/memory",
        max_short_term: int = 20,
        vectorstore: Optional[VectorStore] = None,
    ):
        if hasattr(data_dir, "data_dir"):
            self.data_dir = Path(str(data_dir.data_dir)) / "memory"
        else:
            self.data_dir = Path(str(data_dir))
        self.max_short_term = max_short_term
        self._vectorstore = vectorstore or VectorStore(persist_dir=str(self.data_dir / "vectorstore"))

        # Short-term memory (recent conversation)
        self._short_term: list[ConversationTurn] = []

        # Episodes (significant events)
        self._episodes: list[Episode] = []

        # User profile (learned preferences)
        self._user_profile: dict = {
            "name": None,
            "preferences": {},
            "communication_style": "balanced",
            "topics_of_interest": [],
            "timezone": None,
            "first_interaction": None,
            "total_interactions": 0,
        }

        # Dione's evolving personality state
        self._personality_state: dict = {
            "mood": "neutral",
            "energy": 0.7,
            "curiosity": 0.8,
            "formality": 0.5,
            "recent_topics": [],
        }

    async def initialize(self):
        """Load persisted memory and initialize vectorstore."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        await self._vectorstore.initialize()

        # Load user profile from disk
        profile_path = self.data_dir / "user_profile.json"
        if profile_path.exists():
            with open(profile_path, "r") as f:
                self._user_profile = json.load(f)
            logger.info("Loaded user profile from disk")

        # Load episodes
        episodes_path = self.data_dir / "episodes.json"
        if episodes_path.exists():
            with open(episodes_path, "r") as f:
                data = json.load(f)
                self._episodes = [Episode(**ep) for ep in data]
            logger.info(f"Loaded {len(self._episodes)} episodes")

        # Load personality state
        personality_path = self.data_dir / "personality_state.json"
        if personality_path.exists():
            with open(personality_path, "r") as f:
                self._personality_state = json.load(f)

        logger.info("Memory manager initialized")

    async def save(self):
        """Persist memory to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Save user profile
        with open(self.data_dir / "user_profile.json", "w") as f:
            json.dump(self._user_profile, f, indent=2)

        # Save episodes
        with open(self.data_dir / "episodes.json", "w") as f:
            episodes_data = [
                {
                    "id": ep.id, "title": ep.title,
                    "description": ep.description, "timestamp": ep.timestamp,
                    "category": ep.category, "importance": ep.importance,
                    "metadata": ep.metadata,
                }
                for ep in self._episodes
            ]
            json.dump(episodes_data, f, indent=2)

        # Save personality state
        with open(self.data_dir / "personality_state.json", "w") as f:
            json.dump(self._personality_state, f, indent=2)

        logger.debug("Memory persisted to disk")

    # ------------------------------------------------------------------
    # Short-term memory (conversation window)
    # ------------------------------------------------------------------

    async def add_turn(self, role: str, content: str, sentiment: dict = None) -> ConversationTurn:
        """Add a conversation turn to short-term memory."""
        turn = ConversationTurn(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=time.time(),
            sentiment=sentiment,
        )

        self._short_term.append(turn)

        # If short-term overflows, archive to long-term
        if len(self._short_term) > self.max_short_term:
            overflow = self._short_term[:5]  # Archive oldest 5
            self._short_term = self._short_term[5:]
            await self._archive_to_longterm(overflow)

        # Update interaction count
        if role == "user":
            self._user_profile["total_interactions"] += 1
            if self._user_profile["first_interaction"] is None:
                self._user_profile["first_interaction"] = time.time()

        return turn

    def get_recent_turns(self, n: int = 10) -> list[ConversationTurn]:
        """Get the N most recent conversation turns."""
        return self._short_term[-n:]

    def get_conversation_as_messages(self, n: int = 10) -> list[dict]:
        """Get recent turns formatted for LLM input with strict Gemini turn validation."""
        from server.llm.turn_validator import validate_gemini_turns
        raw = [
            {"role": turn.role, "content": turn.content}
            for turn in self._short_term[-n:]
        ]
        return validate_gemini_turns(raw)

    async def _archive_to_longterm(self, turns: list[ConversationTurn]):
        """Archive old conversation turns to the vector store using fast batch embedding."""
        if not turns:
            return
        texts = [f"[{t.role}] {t.content}" for t in turns]
        metadatas = [
            {
                "role": t.role,
                "timestamp": t.timestamp,
                "date": datetime.fromtimestamp(t.timestamp).isoformat(),
                "sentiment": (t.sentiment or {}).get("label", "neutral"),
            }
            for t in turns
        ]
        ids = [t.id for t in turns]
        await self._vectorstore.add_batch(
            collection="conversations",
            texts=texts,
            metadatas=metadatas,
            ids=ids,
        )
        logger.debug(f"Archived {len(turns)} turns to long-term memory")

    # ------------------------------------------------------------------
    # Long-term memory (semantic retrieval)
    # ------------------------------------------------------------------

    async def recall(self, query: str, n_results: int = 5, limit: Optional[int] = None) -> list[dict]:
        """
        Recall relevant memories for a given query.
        
        Searches across conversations, documents, and knowledge (episodes & facts)
        to find the most relevant context.
        """
        effective_n = limit if limit is not None else n_results
        results = []

        # 1. Search knowledge collection (episodes, facts, user preferences)
        knowledge_results = await self._vectorstore.query(
            collection="knowledge",
            query_text=query,
            n_results=effective_n,
        )
        for r in knowledge_results:
            r["source"] = "knowledge"
        results.extend(knowledge_results)

        # 2. Search conversations
        conv_results = await self._vectorstore.query(
            collection="conversations",
            query_text=query,
            n_results=effective_n,
        )
        for r in conv_results:
            r["source"] = "conversation"
        results.extend(conv_results)

        # 3. Search documents
        doc_results = await self._vectorstore.query(
            collection="documents",
            query_text=query,
            n_results=effective_n,
        )
        for r in doc_results:
            r["source"] = "document"
        results.extend(doc_results)

        # OpenClaw temporal decay reranking
        from server.memory.hybrid_search import calculate_temporal_decay
        now_ts = time.time()
        for r in results:
            meta = r.get("metadata", {}) or {}
            ts = meta.get("timestamp") or meta.get("created_at") or now_ts
            is_evergreen = meta.get("is_evergreen", False) or r.get("source") == "knowledge" or meta.get("type") in ("preference", "identity", "profile")
            try:
                age_days = max(0.0, (now_ts - float(ts)) / (24 * 3600))
            except Exception:
                age_days = 0.0
            decay = calculate_temporal_decay(age_days, half_life_days=30.0, is_evergreen=is_evergreen)
            raw_sim = max(0.0, 1.0 - float(r.get("distance", 0.5)))
            r["score"] = raw_sim * decay

        # Deduplicate near-identical memory snippets (MMR-style diversity filtering) and boost exact keyword hits
        q_tokens = {w.lower() for w in query.split() if len(w) > 2}
        for r in results:
            txt_low = str(r.get("text", "")).lower()
            lexical_hits = sum(1 for t in q_tokens if t in txt_low)
            r["score"] = r.get("score", 0.0) + min(0.25, lexical_hits * 0.06)

        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        diverse_results = []
        seen_prefixes = set()
        for r in results:
            norm_prefix = " ".join(str(r.get("text", "")).lower().split())[:120]
            if norm_prefix and norm_prefix not in seen_prefixes:
                seen_prefixes.add(norm_prefix)
                diverse_results.append(r)
            if len(diverse_results) >= effective_n:
                break

        return diverse_results

    async def store_document(self, text: str, metadata: dict = None) -> str:
        """Store a document in long-term memory."""
        return await self._vectorstore.add(
            collection="documents",
            text=text,
            metadata=metadata or {},
        )

    # ------------------------------------------------------------------
    # Episodic memory (significant events)
    # ------------------------------------------------------------------

    async def remember_episode(
        self,
        title: str,
        description: str,
        category: str = "general",
        importance: float = 0.5,
        metadata: dict = None,
    ) -> Episode:
        """
        Store a significant episode in Dione's memory.
        
        Examples of episodes:
        - "User got promoted" (milestone)
        - "User prefers dark mode" (preference)
        - "User has a meeting with Sarah tomorrow" (task)
        """
        episode = Episode(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            timestamp=time.time(),
            category=category,
            importance=importance,
            metadata=metadata or {},
        )
        self._episodes.append(episode)

        # Also embed in vectorstore for retrieval
        await self._vectorstore.add(
            collection="knowledge",
            text=f"{title}: {description}",
            metadata={
                "type": "episode",
                "category": category,
                "importance": importance,
                "timestamp": episode.timestamp,
            },
            doc_id=episode.id,
        )

        await self.save()
        logger.info(f"Episode remembered: {title}")
        return episode

    def get_recent_episodes(self, n: int = 10, category: str = None) -> list[Episode]:
        """Get recent episodes, optionally filtered by category."""
        episodes = self._episodes
        if category:
            episodes = [ep for ep in episodes if ep.category == category]
        return sorted(episodes, key=lambda ep: ep.timestamp, reverse=True)[:n]

    # ------------------------------------------------------------------
    # User profile
    # ------------------------------------------------------------------

    async def update_user_profile(self, key: str, value):
        """Update a user profile field."""
        if key == "preferences":
            self._user_profile["preferences"].update(value)
        elif key == "topics_of_interest":
            topics = self._user_profile["topics_of_interest"]
            if value not in topics:
                topics.append(value)
                # Keep only last 20 topics
                self._user_profile["topics_of_interest"] = topics[-20:]
        else:
            self._user_profile[key] = value

        await self.save()

    def get_user_profile(self) -> dict:
        """Get the current user profile."""
        return self._user_profile.copy()

    # ------------------------------------------------------------------
    # Dione's personality state
    # ------------------------------------------------------------------

    def get_personality_state(self) -> dict:
        """Get Dione's current personality/mood state."""
        return self._personality_state.copy()

    async def update_personality(self, updates: dict):
        """
        Update Dione's personality state based on interaction.
        
        This is the 'alive' mechanism — Dione's mood and energy
        shift based on interactions, time of day, and user sentiment.
        """
        for key, value in updates.items():
            if key in self._personality_state:
                if isinstance(value, (int, float)):
                    # Smooth transitions (don't jump, drift)
                    old = self._personality_state[key]
                    self._personality_state[key] = old * 0.7 + value * 0.3
                else:
                    self._personality_state[key] = value

        await self.save()

    async def evolve_mood(self, user_sentiment: dict):
        """
        Evolve Dione's mood based on user sentiment analysis.
        
        If the user is happy → Dione becomes more energetic.
        If the user is stressed → Dione becomes calmer, more supportive.
        If the user is angry → Dione becomes more careful, empathetic.
        """
        sentiment_label = user_sentiment.get("label", "neutral")
        urgency = user_sentiment.get("urgency", 0.3)

        mood_map = {
            "positive": {"mood": "cheerful", "energy": 0.8, "formality": 0.4},
            "negative": {"mood": "empathetic", "energy": 0.5, "formality": 0.6},
            "neutral": {"mood": "balanced", "energy": 0.6, "formality": 0.5},
        }

        target = mood_map.get(sentiment_label, mood_map["neutral"])

        # Urgency makes Dione more focused
        if urgency > 0.7:
            target["mood"] = "focused"
            target["formality"] = 0.7

        await self.update_personality(target)

    # ------------------------------------------------------------------
    # Memory statistics
    # ------------------------------------------------------------------

    async def get_stats(self) -> dict:
        """Get memory system statistics."""
        vectorstore_stats = await self._vectorstore.get_stats()
        return {
            "short_term_turns": len(self._short_term),
            "episodes": len(self._episodes),
            "user_interactions": self._user_profile["total_interactions"],
            "personality_mood": self._personality_state["mood"],
            "vectorstore": vectorstore_stats,
        }
