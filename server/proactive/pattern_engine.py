"""
Dione AI — Multi-Scale Temporal Pattern Recognition Engine
==========================================================
Recognizes recurring user behavior across four distinct temporal scales:
1. Hourly: Focus intervals, break habits, and active computing blocks.
2. Daily: Morning task briefings, standup updates, and evening daily summaries.
3. Weekly: Specific day-of-week routines (e.g., Weekly Capstone Mentor Status Email every Monday 9:00 AM).
4. Monthly: End-of-month milestones, monthly progress reports, and review preparations.

Strict Safety Principle:
- Proactively prepares and stages actions as Proposal Cards with 1-click user confirmation.
- Never executes mutating actions (sending emails, modifying files) autonomously.
"""

import time
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from enum import Enum
from loguru import logger


class TimeScale(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class TemporalPattern:
    """A multi-scale temporal pattern recognized by Dione."""
    pattern_id: str
    scale: TimeScale
    name: str                       # e.g., "Weekly Capstone Mentor Status Update"
    description: str                # e.g., "Sends weekly capstone progress email to Prof. Geocey Shejy every Monday 9am"
    action_type: str                # "email_draft", "file_summary", "calendar_prep", "focus_reminder"
    cron_spec: str                  # e.g., "mon 09:00", "daily 08:30", "every 2 hours", "day 28 17:00"
    target: str = ""                # recipient email, project path, etc.
    template_prompt: str = ""       # prompt used to pre-draft the content
    confidence: float = 0.5         # 0.0 to 1.0 (strengthens with repetition & user approvals)
    trigger_count: int = 0
    approved_count: int = 0
    dismissed_count: int = 0
    last_triggered: float = 0.0
    active: bool = True
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scale"] = self.scale.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "TemporalPattern":
        data_copy = dict(data)
        data_copy["scale"] = TimeScale(data_copy.get("scale", "daily"))
        return cls(**data_copy)


class TemporalPatternEngine:
    """
    Multi-Scale Pattern Recognition Engine.
    
    Learns, mines, and tracks patterns across hourly, daily, weekly, and monthly scales.
    """

    def __init__(self, data_dir: str = "data/proactive"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.data_dir / "temporal_patterns.json"
        self.interaction_log_file = self.data_dir / "interaction_history.jsonl"
        
        self.patterns: List[TemporalPattern] = []
        self._load_patterns()
        
        # Ensure default high-value academic and productivity routines are initialized
        self._init_default_patterns()

    def _init_default_patterns(self):
        """Pre-populate authentic academic and personal productivity patterns."""
        if not self.patterns:
            defaults = [
                # 1. Hourly: Focus & Posture Cadence
                TemporalPattern(
                    pattern_id="pat_hourly_focus_01",
                    scale=TimeScale.HOURLY,
                    name="Hourly Focus & Rest Cadence",
                    description="Hourly check-in during intensive engineering coding sessions",
                    action_type="focus_reminder",
                    cron_spec="every 2 hours",
                    template_prompt="Check if user has been coding for 2 hours and suggest a 5-minute break.",
                    confidence=0.85,
                    metadata={"category": "wellness"}
                ),
                # 2. Daily: Morning Briefing & Schedule Preparation
                TemporalPattern(
                    pattern_id="pat_daily_morning_01",
                    scale=TimeScale.DAILY,
                    name="Daily Morning Briefing & Agenda",
                    description="Prepares daily task briefing and calendar schedule every morning at 8:30 AM",
                    action_type="morning_summary",
                    cron_spec="daily 08:30",
                    template_prompt="Summarize today's upcoming meetings, project deadlines, and pending tasks.",
                    confidence=0.92,
                    metadata={"category": "agenda"}
                ),
                # 3. Weekly: Capstone Mentor Status Email to Prof. Geocey Shejy
                TemporalPattern(
                    pattern_id="pat_weekly_mentor_01",
                    scale=TimeScale.WEEKLY,
                    name="Weekly Capstone Mentor Status Email",
                    description="Drafts weekly project progress update email to Prof. Geocey Shejy every Monday at 9:00 AM",
                    action_type="email_draft",
                    cron_spec="mon 09:00",
                    target="geocey.shejy@ves.ac.in",
                    template_prompt=(
                        "Draft a professional weekly progress email to Prof. Geocey Shejy with: "
                        "1. Summary of milestones completed last week (Black book restructuring, testing); "
                        "2. Current work in progress; "
                        "3. Plan for this week and any guidance requested."
                    ),
                    confidence=0.96,
                    metadata={
                        "recipient_name": "Prof. Geocey Shejy",
                        "subject": "Dione AI — Weekly Capstone Project Status Report",
                        "urgency": "normal",
                        "require_confirmation": True
                    }
                ),
                # 4. Monthly: Milestone & Review Preparation
                TemporalPattern(
                    pattern_id="pat_monthly_review_01",
                    scale=TimeScale.MONTHLY,
                    name="Monthly Capstone Milestone & Deliverable Summary",
                    description="Compiles monthly project progress metrics, test results, and Black Book updates on the 28th of every month at 5:00 PM",
                    action_type="monthly_report",
                    cron_spec="day 28 17:00",
                    template_prompt="Compile all test case results, benchmark graphs, and documentation deliverables completed this month.",
                    confidence=0.88,
                    metadata={"category": "milestone"}
                )
            ]
            for p in defaults:
                self.patterns.append(p)
            self._save_patterns()

    def _load_patterns(self):
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                self.patterns = [TemporalPattern.from_dict(p) for p in data]
                logger.info(f"Loaded {len(self.patterns)} multi-scale temporal patterns")
            except Exception as e:
                logger.error(f"Failed to load temporal patterns: {e}")

    def _save_patterns(self):
        try:
            data = [p.to_dict() for p in self.patterns]
            self.storage_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save temporal patterns: {e}")

    def log_interaction(self, event_type: str, details: dict):
        """Log user interaction events for pattern mining."""
        try:
            record = {
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat(),
                "event_type": event_type,
                "details": details
            }
            with open(self.interaction_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.debug(f"Failed to log interaction: {e}")

    def evaluate_triggers(self, now: Optional[datetime] = None) -> List[TemporalPattern]:
        """Check which temporal patterns should trigger at the given time."""
        now = now or datetime.now()
        ready_patterns = []
        
        for p in self.patterns:
            if not p.active or p.confidence < 0.4:
                continue
                
            # Prevent rapid re-triggering within 30 minutes
            if p.last_triggered and (time.time() - p.last_triggered) < 1800:
                continue
                
            if self._matches_schedule(p.cron_spec, now, p.last_triggered):
                ready_patterns.append(p)
                
        return ready_patterns

    def _matches_schedule(self, cron_spec: str, now: datetime, last_triggered: float) -> bool:
        spec = cron_spec.lower().strip()
        
        # 1. "every N hours"
        if "every" in spec and "hour" in spec:
            try:
                parts = spec.split()
                hours = int(parts[1])
                elapsed = time.time() - last_triggered if last_triggered else 999999
                return elapsed >= hours * 3600
            except Exception:
                return False
                
        # 2. "daily HH:MM"
        if spec.startswith("daily"):
            try:
                t_str = spec.split()[1]
                hh, mm = map(int, t_str.split(":"))
                return now.hour == hh and now.minute == mm
            except Exception:
                return False
                
        # 3. "mon HH:MM", "tue HH:MM", etc.
        days = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        for day_name, day_idx in days.items():
            if spec.startswith(day_name):
                if now.weekday() != day_idx:
                    return False
                try:
                    t_str = spec.split()[1]
                    hh, mm = map(int, t_str.split(":"))
                    return now.hour == hh and now.minute == mm
                except Exception:
                    return False
                    
        # 4. "day DD HH:MM" (Monthly)
        if spec.startswith("day"):
            try:
                parts = spec.split()
                day_of_month = int(parts[1])
                t_str = parts[2]
                hh, mm = map(int, t_str.split(":"))
                return now.day == day_of_month and now.hour == hh and now.minute == mm
            except Exception:
                return False
                
        return False

    def feedback(self, pattern_id: str, approved: bool):
        """Update pattern confidence based on user action."""
        for p in self.patterns:
            if p.pattern_id == pattern_id:
                p.trigger_count += 1
                if approved:
                    p.approved_count += 1
                    p.confidence = min(1.0, p.confidence + 0.10)
                    logger.info(f"Pattern '{p.name}' approved! Confidence increased to {p.confidence:.2f}")
                else:
                    p.dismissed_count += 1
                    p.confidence = max(0.1, p.confidence - 0.15)
                    logger.info(f"Pattern '{p.name}' dismissed. Confidence decreased to {p.confidence:.2f}")
                self._save_patterns()
                break
