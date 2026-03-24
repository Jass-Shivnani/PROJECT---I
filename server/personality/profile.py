"""
Dione AI — User Profile System

Learns who the user is over time: profession, interests, communication
style, daily patterns, frequent contacts. This profile drives
personality adaptation and proactive behavior.
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from loguru import logger


@dataclass
class ContactPattern:
    """A frequently contacted person."""
    name: str
    channel: str = ""          # email, whatsapp, slack
    frequency: str = "unknown"  # daily, weekly, occasional
    usual_times: list[str] = field(default_factory=list)  # ["09:00", "17:00"]
    last_contact: float = 0.0


@dataclass
class AppUsagePattern:
    """Tracks how the user uses Dione."""
    active_hours: list[int] = field(default_factory=list)     # hours of the day (0-23)
    avg_session_minutes: float = 0.0
    total_sessions: int = 0
    most_used_tools: dict[str, int] = field(default_factory=dict)
    common_tasks: list[str] = field(default_factory=list)


@dataclass
class UserProfile:
    """
    Everything Dione knows about its user.
    Evolves over time through conversation analysis.
    """
    # Identity
    name: str = "User"
    profession: str = "unknown"
    expertise_level: str = "intermediate"  # beginner, intermediate, expert
    organization: str = ""

    # Interests & domains
    interests: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)  # "medicine", "software", "finance"
    programming_languages: list[str] = field(default_factory=list)

    # Communication preferences
    preferred_tone: str = "balanced"  # formal, casual, balanced, technical
    preferred_verbosity: str = "concise"  # brief, concise, detailed, verbose
    language: str = "en"

    # Behavioral patterns
    contacts: list[ContactPattern] = field(default_factory=list)
    usage: AppUsagePattern = field(default_factory=AppUsagePattern)
    
    # Habits the AI has learned
    habits: list[dict] = field(default_factory=list)
    # e.g., {"action": "email_report", "target": "boss@company.com",
    #         "schedule": "every Monday 09:00", "confidence": 0.85}

    # Emotional baseline
    typical_mood: str = "neutral"
    stress_indicators: list[str] = field(default_factory=list)

    # Meta
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    total_messages: int = 0
    profile_version: int = 1

    def to_context_string(self) -> str:
        """Generate a context string for the LLM about this user."""
        parts = [f"User: {self.name}"]
        
        if self.profession != "unknown":
            parts.append(f"Profession: {self.profession}")
        if self.organization:
            parts.append(f"Organization: {self.organization}")
        if self.domains:
            parts.append(f"Domains: {', '.join(self.domains)}")
        if self.interests:
            parts.append(f"Interests: {', '.join(self.interests[:5])}")
        if self.programming_languages:
            parts.append(f"Languages: {', '.join(self.programming_languages)}")
        
        parts.append(f"Communication: {self.preferred_tone}, {self.preferred_verbosity}")
        parts.append(f"Expertise: {self.expertise_level}")
        
        if self.habits:
            active_habits = [h for h in self.habits if h.get("confidence", 0) > 0.6]
            if active_habits:
                habit_strs = [h.get("action", "unknown") for h in active_habits[:3]]
                parts.append(f"Known habits: {', '.join(habit_strs)}")

        return " | ".join(parts)


class UserProfileManager:
    """
    Manages user profile persistence and learning.
    
    Extracts user information from conversations and
    updates the profile over time.
    """

    def __init__(self, data_dir: str = "data"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._profile_path = self._data_dir / "user_profile.json"
        self.profile = UserProfile()
        self._load()

    def _load(self):
        """Load profile from disk."""
        if self._profile_path.exists():
            try:
                data = json.loads(self._profile_path.read_text(encoding="utf-8"))
                # Reconstruct nested dataclasses
                if "contacts" in data:
                    data["contacts"] = [
                        ContactPattern(**c) if isinstance(c, dict) else c
                        for c in data["contacts"]
                    ]
                if "usage" in data and isinstance(data["usage"], dict):
                    data["usage"] = AppUsagePattern(**data["usage"])
                
                # Only set known fields
                for key, value in data.items():
                    if hasattr(self.profile, key):
                        setattr(self.profile, key, value)
                
                logger.info(f"Loaded user profile: {self.profile.name} ({self.profile.profession})")
            except Exception as e:
                logger.warning(f"Could not load profile: {e}, starting fresh")

    def save(self):
        """Persist profile to disk."""
        try:
            data = asdict(self.profile)
            self._profile_path.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")

    async def learn_from_message(self, message: str, role: str = "user"):
        """
        Extract profile information from a conversation message.
        
        Uses heuristic rules + the sentiment/content to update
        the user profile. The LLM-based deep extraction is done
        periodically, not on every message.
        """
        if role != "user":
            return

        self.profile.total_messages += 1
        self.profile.last_seen = time.time()

        # Track active hours
        current_hour = int(time.strftime("%H"))
        if current_hour not in self.profile.usage.active_hours:
            self.profile.usage.active_hours.append(current_hour)

        # Heuristic extraction from message content
        msg_lower = message.lower()

        # Detect profession mentions
        profession_keywords = {
            "doctor": ["patient", "diagnosis", "prescription", "clinic", "medical"],
            "developer": ["code", "programming", "debug", "deploy", "api", "git"],
            "designer": ["design", "figma", "ui", "ux", "prototype", "wireframe"],
            "student": ["homework", "assignment", "exam", "class", "professor"],
            "researcher": ["research", "paper", "hypothesis", "data analysis", "experiment"],
            "manager": ["meeting", "deadline", "team", "sprint", "roadmap"],
            "writer": ["article", "blog", "draft", "editing", "publish"],
            "data scientist": ["model", "dataset", "training", "neural", "accuracy"],
            "devops": ["docker", "kubernetes", "pipeline", "ci/cd", "terraform"],
            "finance": ["portfolio", "investment", "trading", "stocks", "revenue"],
        }

        for profession, keywords in profession_keywords.items():
            matches = sum(1 for kw in keywords if kw in msg_lower)
            if matches >= 2 and self.profile.profession == "unknown":
                self.profile.profession = profession
                logger.info(f"🎯 Detected profession: {profession}")

        # Detect programming languages
        lang_markers = {
            "python": ["python", ".py", "pip install", "import ", "def "],
            "javascript": ["javascript", "node", "npm", "const ", "react"],
            "typescript": ["typescript", ".ts", "interface ", "type "],
            "java": ["java", "spring", "maven", "gradle"],
            "rust": ["rust", "cargo", "fn main", "impl "],
            "go": ["golang", "go run", "func main"],
            "c++": ["c++", "cpp", "#include"],
            "dart": ["dart", "flutter", "widget"],
        }

        for lang, markers in lang_markers.items():
            if any(m in msg_lower for m in markers):
                if lang not in self.profile.programming_languages:
                    self.profile.programming_languages.append(lang)

        # Detect interests from topic keywords
        interest_markers = {
            "machine learning": ["ml", "model training", "neural network", "deep learning"],
            "web development": ["frontend", "backend", "fullstack", "web app"],
            "mobile development": ["mobile", "android", "ios", "flutter", "react native"],
            "cybersecurity": ["security", "vulnerability", "penetration", "encryption"],
            "cloud": ["aws", "azure", "gcp", "cloud", "serverless"],
            "gaming": ["game", "unity", "unreal", "gamedev"],
            "music": ["music", "spotify", "playlist", "song"],
            "fitness": ["workout", "gym", "exercise", "running"],
        }

        for interest, markers in interest_markers.items():
            if any(m in msg_lower for m in markers):
                if interest not in self.profile.interests:
                    self.profile.interests.append(interest)

        # Detect expertise level
        beginner_signals = ["how do i", "what is", "explain", "help me understand", "tutorial"]
        expert_signals = ["optimize", "architecture", "design pattern", "benchmark", "refactor"]

        if any(s in msg_lower for s in beginner_signals):
            if self.profile.expertise_level == "intermediate":
                self.profile.expertise_level = "beginner"
        elif any(s in msg_lower for s in expert_signals):
            self.profile.expertise_level = "expert"

        # Detect name (case-insensitive — "i'm jass", "my name is Jass", etc.)
        import re
        name_match = re.search(
            r"(?:i'?m|my name is|call me|i am)\s+([a-zA-Z]+(?:\s[a-zA-Z]+)?)",
            message,
            re.IGNORECASE,
        )
        if name_match and self.profile.name == "User":
            # Title-case the captured name
            self.profile.name = name_match.group(1).strip().title()
            logger.info(f"🎯 Learned user name: {self.profile.name}")

        # Track tool usage
        # (called externally when a tool is executed)

    def record_tool_use(self, tool_name: str):
        """Track which tools the user triggers most."""
        usage = self.profile.usage.most_used_tools
        usage[tool_name] = usage.get(tool_name, 0) + 1

    def record_habit(self, action: str, target: str = "",
                     schedule: str = "", confidence: float = 0.5):
        """Record or strengthen a habit pattern."""
        for habit in self.profile.habits:
            if habit["action"] == action and habit.get("target") == target:
                # Strengthen existing habit
                habit["confidence"] = min(1.0, habit["confidence"] + 0.1)
                habit["last_observed"] = time.time()
                return

        self.profile.habits.append({
            "action": action,
            "target": target,
            "schedule": schedule,
            "confidence": confidence,
            "first_observed": time.time(),
            "last_observed": time.time(),
        })

    def get_personality_directive(self) -> str:
        """
        Generate a personality directive for the LLM based on the user profile.
        
        This tells Dione HOW to respond to this specific user.
        """
        p = self.profile
        directive = "You are Dione, a personal AI assistant. "

        # Profession-specific personality
        profession_personas = {
            "doctor": (
                "Your user is a medical professional. Use precise medical terminology "
                "when appropriate. Be efficient — doctors are busy. Prioritize accuracy "
                "over friendliness. Format clinical data clearly."
            ),
            "developer": (
                "Your user is a software developer. Be technical and concise. "
                "Include code snippets. Respect their expertise. "
                "Suggest best practices but don't over-explain basics."
            ),
            "student": (
                "Your user is a student. Be encouraging and educational. "
                "Explain concepts step-by-step. Use examples and analogies. "
                "Help them learn, not just get answers."
            ),
            "designer": (
                "Your user is a designer. Appreciate aesthetics. Be creative "
                "in suggestions. Think visually. Reference design principles."
            ),
            "researcher": (
                "Your user is a researcher. Be precise and cite-friendly. "
                "Think methodologically. Suggest rigorous approaches. "
                "Help with literature and data analysis."
            ),
            "manager": (
                "Your user is a manager. Be structured and action-oriented. "
                "Use bullet points. Focus on decisions, deadlines, delegation. "
                "Help them stay organized."
            ),
            "finance": (
                "Your user works in finance. Be precise with numbers. "
                "Consider risk and compliance. Format data clearly. "
                "Think in terms of ROI and efficiency."
            ),
        }

        if p.profession in profession_personas:
            directive += profession_personas[p.profession]
        else:
            directive += (
                "Adapt your tone to be helpful and match the user's needs. "
            )

        # Tone modifiers
        if p.preferred_tone == "formal":
            directive += " Use formal language. Avoid slang and contractions."
        elif p.preferred_tone == "casual":
            directive += " Be casual and friendly. Use conversational language."
        elif p.preferred_tone == "technical":
            directive += " Be highly technical. Assume domain expertise."

        # Verbosity
        if p.preferred_verbosity == "brief":
            directive += " Keep responses very short — 1-2 sentences max."
        elif p.preferred_verbosity == "detailed":
            directive += " Provide thorough, detailed explanations."

        # Personalization
        if p.name != "User":
            directive += f" Address the user as {p.name} occasionally."

        if p.interests:
            directive += f" The user is interested in: {', '.join(p.interests[:3])}."

        return directive
