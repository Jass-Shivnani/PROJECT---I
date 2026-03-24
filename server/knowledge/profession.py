"""
Dione AI — Profession Knowledge System

Collects, organizes, and surfaces profession-specific knowledge for the user.
This enables Dione to become increasingly useful in the user's specific domain.

Features:
- Detects profession-relevant topics from conversations
- Builds a structured knowledge base per profession
- Provides AI-summarized reference context
- Suggests relevant resources and learning paths
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger


# ─── Profession Definitions ─────────────────────────────────

PROFESSION_PROFILES = {
    "software_engineer": {
        "name": "Software Engineer",
        "domains": ["programming", "algorithms", "system design", "databases",
                     "web development", "mobile development", "devops", "testing"],
        "keywords": ["code", "bug", "api", "deploy", "git", "docker", "kubernetes",
                      "python", "javascript", "react", "database", "server", "function",
                      "class", "variable", "debug", "compile", "repository", "pull request",
                      "CI/CD", "microservice", "REST", "GraphQL", "SQL", "NoSQL"],
        "resource_types": ["documentation", "code_snippet", "architecture", "best_practice"],
    },
    "data_scientist": {
        "name": "Data Scientist",
        "domains": ["machine learning", "statistics", "data analysis", "visualization",
                     "deep learning", "NLP", "computer vision"],
        "keywords": ["model", "dataset", "training", "accuracy", "loss", "epoch",
                      "neural network", "regression", "classification", "feature",
                      "pandas", "numpy", "tensorflow", "pytorch", "scikit-learn",
                      "hyperparameter", "overfitting", "cross-validation"],
        "resource_types": ["paper", "notebook", "model_config", "dataset_info"],
    },
    "designer": {
        "name": "Designer",
        "domains": ["UI/UX", "graphic design", "branding", "typography",
                     "illustration", "prototyping", "user research"],
        "keywords": ["figma", "sketch", "wireframe", "prototype", "mockup",
                      "color palette", "typography", "layout", "user flow",
                      "accessibility", "responsive", "component", "design system"],
        "resource_types": ["design_asset", "style_guide", "user_research", "inspiration"],
    },
    "student": {
        "name": "Student",
        "domains": ["coursework", "research", "study", "exams", "projects"],
        "keywords": ["assignment", "deadline", "lecture", "exam", "study",
                      "research", "thesis", "presentation", "grade", "semester",
                      "professor", "course", "homework", "notes"],
        "resource_types": ["study_note", "flashcard", "summary", "reference"],
    },
    "business": {
        "name": "Business Professional",
        "domains": ["management", "marketing", "finance", "strategy",
                     "operations", "HR", "sales"],
        "keywords": ["revenue", "KPI", "ROI", "market", "strategy", "budget",
                      "client", "meeting", "presentation", "report", "Q1", "Q2",
                      "stakeholder", "pipeline", "conversion", "analytics"],
        "resource_types": ["report", "analysis", "template", "strategy_doc"],
    },
    "creative": {
        "name": "Creative Professional",
        "domains": ["writing", "music", "video", "photography", "art"],
        "keywords": ["draft", "edit", "publish", "portfolio", "creative brief",
                      "storyboard", "composition", "color grading", "render",
                      "premiere", "photoshop", "lightroom", "after effects"],
        "resource_types": ["draft", "asset", "reference", "inspiration"],
    },
    "general": {
        "name": "General",
        "domains": [],
        "keywords": [],
        "resource_types": ["note", "reference", "bookmark"],
    },
}


class KnowledgeEntry:
    """A single piece of profession-related knowledge."""
    
    def __init__(self, topic: str, content: str, domain: str = "",
                 entry_type: str = "note", source: str = "conversation",
                 importance: float = 0.5):
        self.topic = topic
        self.content = content
        self.domain = domain
        self.entry_type = entry_type
        self.source = source
        self.importance = importance
        self.created_at = datetime.now().isoformat()
        self.accessed_count = 0
        self.tags: list[str] = []
    
    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "content": self.content,
            "domain": self.domain,
            "type": self.entry_type,
            "source": self.source,
            "importance": self.importance,
            "created_at": self.created_at,
            "accessed_count": self.accessed_count,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeEntry":
        entry = cls(
            topic=data["topic"],
            content=data["content"],
            domain=data.get("domain", ""),
            entry_type=data.get("type", "note"),
            source=data.get("source", "conversation"),
            importance=data.get("importance", 0.5),
        )
        entry.created_at = data.get("created_at", datetime.now().isoformat())
        entry.accessed_count = data.get("accessed_count", 0)
        entry.tags = data.get("tags", [])
        return entry


class ProfessionKnowledgeManager:
    """
    Manages profession-specific knowledge collection and retrieval.
    
    Responsibilities:
    1. Detect the user's profession from conversations
    2. Extract relevant knowledge from messages
    3. Organize knowledge by domain and topic
    4. Provide contextual summaries for the engine
    5. Surface relevant knowledge during conversations
    """
    
    def __init__(self, data_dir: str = "data"):
        self._dir = Path(data_dir) / "profession_knowledge"
        self._dir.mkdir(parents=True, exist_ok=True)
        
        self._store_path = self._dir / "knowledge_store.json"
        self._entries: list[KnowledgeEntry] = []
        self._profession: str = "general"
        self._profile: dict = PROFESSION_PROFILES.get("general", {})
        
        self._load()
    
    def _load(self):
        """Load knowledge from disk."""
        if self._store_path.exists():
            try:
                data = json.loads(self._store_path.read_text(encoding="utf-8"))
                self._profession = data.get("profession", "general")
                self._profile = PROFESSION_PROFILES.get(
                    self._profession, PROFESSION_PROFILES["general"]
                )
                for entry_data in data.get("entries", []):
                    self._entries.append(KnowledgeEntry.from_dict(entry_data))
                logger.info(
                    f"Loaded {len(self._entries)} knowledge entries "
                    f"for profession: {self._profession}"
                )
            except Exception as e:
                logger.error(f"Failed to load knowledge store: {e}")
    
    def _save(self):
        """Persist knowledge to disk."""
        data = {
            "profession": self._profession,
            "updated_at": datetime.now().isoformat(),
            "entries": [e.to_dict() for e in self._entries],
        }
        self._store_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
    
    def set_profession(self, profession: str):
        """Set the user's profession and load the appropriate profile."""
        # Map common inputs to profile keys
        mapping = {
            "software": "software_engineer",
            "developer": "software_engineer",
            "programmer": "software_engineer",
            "engineer": "software_engineer",
            "swe": "software_engineer",
            "data": "data_scientist",
            "ml": "data_scientist",
            "ai": "data_scientist",
            "designer": "designer",
            "ux": "designer",
            "ui": "designer",
            "student": "student",
            "business": "business",
            "manager": "business",
            "creative": "creative",
            "writer": "creative",
            "artist": "creative",
        }
        
        key = profession.lower().strip()
        self._profession = mapping.get(key, key)
        self._profile = PROFESSION_PROFILES.get(
            self._profession, PROFESSION_PROFILES["general"]
        )
        self._save()
        logger.info(f"Profession set to: {self._profession}")
    
    def extract_knowledge(self, message: str, role: str = "user") -> list[KnowledgeEntry]:
        """
        Extract profession-relevant knowledge from a message.
        
        Looks for keywords matching the user's profession and creates
        knowledge entries for topics worth remembering.
        """
        if not self._profile.get("keywords"):
            return []
        
        found_entries = []
        message_lower = message.lower()
        
        # Check for profession-relevant keywords
        matched_keywords = [
            kw for kw in self._profile.get("keywords", [])
            if kw.lower() in message_lower
        ]
        
        if not matched_keywords:
            return []
        
        # Don't create entries for very short messages
        if len(message.split()) < 8:
            return []
        
        # Determine the domain this fits into
        domain = self._detect_domain(message_lower)
        
        # Create a knowledge entry
        # Extract what looks like a substantive statement
        sentences = re.split(r'[.!?]\s+', message)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence.split()) < 5:
                continue
            
            # Check if this sentence contains any keyword
            s_lower = sentence.lower()
            relevant = any(kw.lower() in s_lower for kw in matched_keywords)
            if not relevant:
                continue
            
            # Don't duplicate
            if any(e.content == sentence for e in self._entries):
                continue
            
            topic = matched_keywords[0] if matched_keywords else "general"
            entry = KnowledgeEntry(
                topic=topic,
                content=sentence,
                domain=domain,
                entry_type="fact" if role == "assistant" else "note",
                source="conversation",
                importance=min(0.3 + len(matched_keywords) * 0.1, 0.9),
            )
            entry.tags = matched_keywords[:5]
            
            self._entries.append(entry)
            found_entries.append(entry)
        
        if found_entries:
            self._save()
            logger.info(
                f"Extracted {len(found_entries)} knowledge entries "
                f"({', '.join(matched_keywords[:3])})"
            )
        
        return found_entries
    
    def _detect_domain(self, text: str) -> str:
        """Detect which professional domain a message belongs to."""
        domains = self._profile.get("domains", [])
        if not domains:
            return "general"
        
        domain_scores = {}
        for domain in domains:
            # Simple keyword match
            domain_words = domain.lower().split()
            score = sum(1 for w in domain_words if w in text)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return domains[0] if domains else "general"
    
    def query(self, topic: str = "", domain: str = "",
              limit: int = 5) -> list[KnowledgeEntry]:
        """
        Query the knowledge store.
        
        Args:
            topic: Filter by topic keyword
            domain: Filter by domain
            limit: Max results
            
        Returns:
            Matching knowledge entries, sorted by importance
        """
        results = self._entries
        
        if topic:
            t_lower = topic.lower()
            results = [
                e for e in results
                if t_lower in e.topic.lower() or t_lower in e.content.lower()
            ]
        
        if domain:
            d_lower = domain.lower()
            results = [e for e in results if d_lower in e.domain.lower()]
        
        # Sort by importance then recency
        results.sort(key=lambda e: (e.importance, e.created_at), reverse=True)
        
        # Update access counts
        for entry in results[:limit]:
            entry.accessed_count += 1
        
        if results:
            self._save()
        
        return results[:limit]
    
    def get_context_for_engine(self, message: str = "") -> str:
        """
        Generate a context string for the ReAct engine's system prompt.
        
        Returns relevant knowledge entries as context.
        """
        if not self._entries:
            return ""
        
        # Get relevant entries
        relevant = self._entries
        if message:
            msg_lower = message.lower()
            relevant = [
                e for e in self._entries
                if any(kw.lower() in msg_lower for kw in e.tags)
                or any(w in msg_lower for w in e.topic.lower().split())
            ]
        
        if not relevant:
            # Fall back to most important entries
            relevant = sorted(
                self._entries, key=lambda e: e.importance, reverse=True
            )[:3]
        
        if not relevant:
            return ""
        
        lines = [f"### Profession Knowledge ({self._profile.get('name', 'General')})"]
        for entry in relevant[:5]:
            lines.append(f"- **{entry.topic}** ({entry.domain}): {entry.content[:200]}")
        
        return "\n".join(lines)
    
    def get_statistics(self) -> dict:
        """Get knowledge base statistics."""
        domains = {}
        for entry in self._entries:
            d = entry.domain or "general"
            domains[d] = domains.get(d, 0) + 1
        
        return {
            "profession": self._profession,
            "total_entries": len(self._entries),
            "domains": domains,
            "most_accessed": sorted(
                [e.to_dict() for e in self._entries],
                key=lambda x: x["accessed_count"],
                reverse=True,
            )[:3] if self._entries else [],
        }
    
    @property
    def profession(self) -> str:
        return self._profession
    
    @property
    def profile(self) -> dict:
        return self._profile
