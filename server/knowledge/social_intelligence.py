"""
Dione AI — Social & Relationship Intelligence Engine
====================================================
Elevates contact memory into an interconnected social and commitment graph:
1. Rich Person Dossiers: Aliasing, roles, preferred communication tones, and salutation templates.
2. Commitment & Promise Tracking: Detects promised deliverables ("I'll send the report by Wednesday") and tracks deadlines.
3. Dynamic Tone Adaptation: Adapts draft tone automatically (e.g., Formal Academic for Mentors vs. Casual Collaborative for Teammates).
4. Relationship Health & Decay Monitoring: Proactively suggests touchpoints before important relationships go cold.
5. Unified Multi-Channel Identity: Merges Email, WhatsApp, Roll Numbers, and Nicknames into canonical nodes.
"""

import re
import time
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
from enum import Enum
from loguru import logger

from server.knowledge.entities import Entity, EntityType
from server.knowledge.relations import Relation, RelationType


class RelationshipCategory(Enum):
    MENTOR_PROFESSOR = "mentor_professor"
    PEER_TEAMMATE = "peer_teammate"
    HEAD_OF_DEPT = "head_of_dept"
    EXTERNAL_EXAMINER = "external_examiner"
    FAMILY_FRIEND = "family_friend"
    PROFESSIONAL_CONTACT = "professional_contact"
    LEAD_DEVELOPER = "lead_developer"
    PEER_COLLEAGUE = "peer_colleague"


@dataclass
class Commitment:
    """A promise or deadline owed to/from a contact."""
    commitment_id: str
    person_name: str
    person_email: str
    description: str             # e.g., "Send revised Chapter 6 draft"
    due_date: str                # ISO or human string e.g. "2026-09-03"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"      # "pending", "completed", "overdue", "dismissed"
    priority: str = "normal"     # "normal", "high", "urgent"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Commitment":
        return cls(**data)


@dataclass
class PersonDossier:
    """A comprehensive profile of a contact in the user's social graph."""
    person_id: str
    canonical_name: str
    category: RelationshipCategory
    email: str
    phone: str = ""
    role: str = ""
    organization: str = ""
    aliases: List[str] = field(default_factory=list)
    preferred_tone: str = "formal_academic"  # "formal_academic", "casual_peer", "high_formal"
    salutation_template: str = "Dear Sir/Madam,"
    valediction_template: str = "Regards,\nJass"
    commitments: List[Commitment] = field(default_factory=list)
    interaction_count: int = 0
    last_contacted: str = field(default_factory=lambda: datetime.now().isoformat())
    touchpoint_cadence_days: int = 7         # e.g. touchpoint every 7 days with mentor
    sentiment_history: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["commitments"] = [c.to_dict() for c in self.commitments]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "PersonDossier":
        data_copy = dict(data)
        raw_cat = str(data_copy.get("category", "peer_teammate")).lower()
        try:
            data_copy["category"] = RelationshipCategory(raw_cat)
        except ValueError:
            data_copy["category"] = RelationshipCategory.PEER_TEAMMATE

        data_copy["commitments"] = [Commitment.from_dict(c) for c in data_copy.get("commitments", [])]
        return cls(**data_copy)


class SocialIntelligenceEngine:
    """
    Manages Social Graphs, Commitment Tracking, and Contextual Tone Adaptation.
    """

    def __init__(self, knowledge_graph=None, storage_path: str = "data/social/dossiers.json"):
        self.kg = knowledge_graph
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.dossiers: Dict[str, PersonDossier] = {}
        self._load_dossiers()
        self._init_default_academic_circle()

    def set_knowledge_graph(self, kg):
        self.kg = kg

    def _init_default_academic_circle(self):
        """Pre-populate authentic VESIT capstone academic circle."""
        if not self.dossiers:
            # 1. Project Mentor: Prof. Geocey Shejy
            mentor = PersonDossier(
                person_id="person_geocey",
                canonical_name="Prof. Geocey Shejy",
                category=RelationshipCategory.MENTOR_PROFESSOR,
                email="geocey.shejy@ves.ac.in",
                role="Technical Advisor & Assistant Professor",
                organization="VESIT Computer Engineering",
                aliases=["Geocey", "Prof. Geocey", "Prof. Shejy", "Mentor", "Guide", "Project Guide"],
                preferred_tone="formal_academic",
                salutation_template="Respected Ma'am,",
                valediction_template="Sincerely,\nJass Shivnani",
                touchpoint_cadence_days=7,
                commitments=[
                    Commitment(
                        commitment_id="comm_01",
                        person_name="Prof. Geocey Shejy",
                        person_email="geocey.shejy@ves.ac.in",
                        description="Share autonomous runtime benchmarks and multi-agent architecture telemetry",
                        due_date=(datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
                        priority="high"
                    )
                ]
            )
            self.dossiers[mentor.person_id] = mentor

            # 2. HOD: Dr. Mrs. Nupur Giri
            hod = PersonDossier(
                person_id="person_nupur",
                canonical_name="Dr. Mrs. Nupur Giri",
                category=RelationshipCategory.HEAD_OF_DEPT,
                email="nupur.giri@ves.ac.in",
                role="Head of Department",
                organization="VESIT Computer Engineering",
                aliases=["Dr. Nupur Giri", "HOD Ma'am", "HOD", "Nupur Ma'am"],
                preferred_tone="high_formal",
                salutation_template="Respected HOD Ma'am,",
                valediction_template="Yours faithfully,\nJass Shivnani",
                touchpoint_cadence_days=21
            )
            self.dossiers[hod.person_id] = hod

            # 3. Teammate: Riya Khialani
            riya = PersonDossier(
                person_id="person_riya",
                canonical_name="Riya Khialani",
                category=RelationshipCategory.PEER_TEAMMATE,
                email="riyakhialani@gmail.com",
                phone="9699749462",
                role="Systems Engineering Collaborator",
                organization="VESIT Computer Engineering",
                aliases=["Riya", "Riya K", "Khialani"],
                preferred_tone="casual_peer",
                salutation_template="Hey Riya,",
                valediction_template="Cheers,\nJass",
                touchpoint_cadence_days=2
            )
            self.dossiers[riya.person_id] = riya

            # 4. Teammate: Khushi Sadhuramani
            khushi = PersonDossier(
                person_id="person_khushi",
                canonical_name="Khushi Sadhuramani",
                category=RelationshipCategory.PEER_TEAMMATE,
                email="khushi.sadhuramani@ves.ac.in",
                phone="+91 98331 45290",
                role="Systems Engineering Collaborator",
                organization="VESIT Computer Engineering",
                aliases=["Khushi", "Khushi S"],
                preferred_tone="casual_peer",
                salutation_template="Hey Khushi,",
                valediction_template="Cheers,\nJass",
                touchpoint_cadence_days=3
            )
            self.dossiers[khushi.person_id] = khushi

            # 5. Teammate: Ruchika Dingria
            ruchika = PersonDossier(
                person_id="person_ruchika",
                canonical_name="Ruchika Dingria",
                category=RelationshipCategory.PEER_TEAMMATE,
                email="ruchika.dingria@ves.ac.in",
                phone="+91 98192 78314",
                role="Systems Engineering Collaborator",
                organization="VESIT Computer Engineering",
                aliases=["Ruchika", "Ruchika D"],
                preferred_tone="casual_peer",
                salutation_template="Hey Ruchika,",
                valediction_template="Cheers,\nJass",
                touchpoint_cadence_days=3
            )
            self.dossiers[ruchika.person_id] = ruchika

            # 6. Lead: Jass Shivnani
            jass = PersonDossier(
                person_id="person_jass",
                canonical_name="Jass Shivnani",
                category=RelationshipCategory.LEAD_DEVELOPER,
                email="jass.shivnani@ves.ac.in",
                phone="+91 98200 12345",
                role="Lead Systems Architect & Core Developer",
                organization="VESIT Computer Engineering",
                aliases=["Jass", "Lead", "Architect"],
                preferred_tone="direct_technical",
                salutation_template="Hey Jass,",
                valediction_template="Best,\nDione",
                touchpoint_cadence_days=1
            )
            self.dossiers[jass.person_id] = jass

            # 7. Peer: Rushil Rohra
            rushil = PersonDossier(
                person_id="person_rushil",
                canonical_name="Rushil Rohra",
                category=RelationshipCategory.PEER_COLLEAGUE,
                email="rushil.rohra11@gmail.com",
                phone="+91 98765 43210",
                role="Engineering Peer & Data Mining Colleague",
                organization="VESIT",
                aliases=["Rushil", "Rushil R"],
                preferred_tone="friendly_peer",
                salutation_template="Hey Rushil,",
                valediction_template="Best,\nJass",
                touchpoint_cadence_days=5
            )
            self.dossiers[rushil.person_id] = rushil

            self._save_dossiers()

    def _load_dossiers(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for pid, pdata in data.items():
                    d = PersonDossier.from_dict(pdata)
                    seen_comms = set()
                    unique_comms = []
                    for c in d.commitments:
                        key = (c.description.strip().lower(), c.status)
                        if key not in seen_comms:
                            seen_comms.add(key)
                            unique_comms.append(c)
                    d.commitments = unique_comms
                    self.dossiers[pid] = d
                logger.info(f"Loaded {len(self.dossiers)} social dossiers")
            except Exception as e:
                logger.error(f"Failed to load social dossiers: {e}")

    def _save_dossiers(self):
        try:
            data = {pid: d.to_dict() for pid, d in self.dossiers.items()}
            self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save social dossiers: {e}")

    # ------------------------------------------------------------------
    # Canonical Entity Resolution & Aliasing
    # ------------------------------------------------------------------

    def resolve_person(self, query: str) -> Optional[PersonDossier]:
        """
        Resolve any alias, nickname, role, or partial name to the canonical PersonDossier.
        Example: 'mentor' -> Prof. Geocey Shejy, 'HOD' -> Dr. Mrs. Nupur Giri
        """
        q = query.lower().strip()
        
        # 1. Exact email match
        for d in self.dossiers.values():
            if d.email and d.email.lower() == q:
                return d
                
        # 2. Canonical name or alias match
        for d in self.dossiers.values():
            if q == d.canonical_name.lower() or any(q == alias.lower() for alias in d.aliases):
                return d
                
        # 3. Partial substring match
        for d in self.dossiers.values():
            if q in d.canonical_name.lower() or any(q in alias.lower() for alias in d.aliases):
                return d
                
        return None

    # ------------------------------------------------------------------
    # Dynamic Tone Adaptation for LLM Prompts
    # ------------------------------------------------------------------

    def get_tone_guidance(self, recipient_query: str) -> str:
        """
        Produce specialized system prompt directives tailored to the recipient's relationship.
        """
        dossier = self.resolve_person(recipient_query)
        if not dossier:
            return "Maintain a polite, professional, and clear communication tone."

        directives = [
            f"RECIPIENT DOSSIER: {dossier.canonical_name} ({dossier.role})",
            f"RELATIONSHIP: {dossier.category.value.replace('_', ' ').title()}",
            f"MANDATORY SALUTATION: '{dossier.salutation_template}'",
            f"MANDATORY SIGN-OFF: '{dossier.valediction_template}'",
        ]

        if dossier.category == RelationshipCategory.MENTOR_PROFESSOR:
            directives.append(
                "TONE DIRECTIVE: Highly structured, respectful, academic. Use clear numbered progress bullets. "
                "Explicitly highlight milestones completed, work in progress, and ask for specific review feedback."
            )
        elif dossier.category == RelationshipCategory.HEAD_OF_DEPT:
            directives.append(
                "TONE DIRECTIVE: Formal departmental correspondence. Concise, respectful, adhering to college protocol."
            )
        elif dossier.category == RelationshipCategory.PEER_TEAMMATE:
            directives.append(
                "TONE DIRECTIVE: Casual, clear, collaborative. Get straight to the point without unnecessary formalities."
            )

        # Append any active commitments
        pending_comms = [c for c in dossier.commitments if c.status == "pending"]
        if pending_comms:
            directives.append("ACTIVE COMMITMENTS / PROMISES OWED TO THIS PERSON:")
            for c in pending_comms:
                directives.append(f"  • {c.description} (Due: {c.due_date})")

        return "\n".join(directives)

    # ------------------------------------------------------------------
    # Automated Commitment / Promise Mining
    # ------------------------------------------------------------------

    def detect_and_record_commitments(self, text: str, recipient_hint: str = "") -> List[Commitment]:
        """
        Mine conversational text for promised actions and deadlines.
        """
        commitment_patterns = [
            r"(?:I will|I'll|will|shall)\s+(?:send|share|email|update|deliver|prepare|finish|complete)\s+(?:the\s+)?([^\.,;\n]+?)(?:\s+(?:by|before|on|tomorrow|next week)\s+([^\.,;\n]+))?[\.,;\n]",
            r"(?:let me|allow me to)\s+(?:review|check|fix|send)\s+([^\.,;\n]+?)(?:\s+(?:by|before)\s+([^\.,;\n]+))?[\.,;\n]"
        ]
        
        found = []
        dossier = self.resolve_person(recipient_hint) if recipient_hint else None
        
        for pat in commitment_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                desc = m.group(1).strip()
                due = m.group(2).strip() if (m.lastindex >= 2 and m.group(2)) else "upcoming"
                
                desc_clean = desc.capitalize()
                
                # Check if a pending commitment with the same description already exists
                already_exists = False
                if dossier:
                    already_exists = any(
                        c_exist.description.lower() == desc_clean.lower() and c_exist.status == "pending"
                        for c_exist in dossier.commitments
                    )
                
                if already_exists:
                    continue

                cid = f"comm_{int(time.time())}_{len(found)}"
                c = Commitment(
                    commitment_id=cid,
                    person_name=dossier.canonical_name if dossier else (recipient_hint or "Recipient"),
                    person_email=dossier.email if dossier else "",
                    description=desc_clean,
                    due_date=due
                )
                found.append(c)
                
                if dossier:
                    dossier.commitments.append(c)
                    
                # Link in Knowledge Graph if attached
                if self.kg and dossier:
                    if dossier.person_id not in self.kg.graph:
                        self.kg.add_entity(Entity(
                            id=dossier.person_id,
                            type=EntityType.PERSON,
                            name=dossier.canonical_name,
                            metadata={"role": dossier.role, "email": dossier.email}
                        ))
                    comm_entity = Entity(
                        id=cid,
                        type=EntityType.COMMITMENT,
                        name=f"Commitment: {desc_clean}",
                        metadata={"due": due, "person": dossier.canonical_name, "status": "pending"}
                    )
                    self.kg.add_entity(comm_entity)
                    self.kg.add_relation(Relation(
                        id=f"rel_{cid}_{dossier.person_id}",
                        source_id=cid,
                        target_id=dossier.person_id,
                        relation_type=RelationType.PROMISED_TO,
                        weight=1.0
                    ))

        if found:
            self._save_dossiers()
            logger.info(f"🤝 Mined {len(found)} new commitments from text.")
        return found

    # ------------------------------------------------------------------
    # Relationship Health & Touchpoint Decay Evaluator
    # ------------------------------------------------------------------

    def evaluate_relationship_health(self) -> List[Dict]:
        """
        Identify VIP relationships that have exceeded their expected touchpoint cadence.
        """
        now = datetime.now()
        alerts = []
        
        for pid, d in self.dossiers.items():
            if d.category in [RelationshipCategory.MENTOR_PROFESSOR, RelationshipCategory.PEER_TEAMMATE]:
                try:
                    last_dt = datetime.fromisoformat(d.last_contacted)
                    days_elapsed = (now - last_dt).days
                    if days_elapsed >= d.touchpoint_cadence_days:
                        alerts.append({
                            "person_id": pid,
                            "name": d.canonical_name,
                            "role": d.role,
                            "days_elapsed": days_elapsed,
                            "cadence": d.touchpoint_cadence_days,
                            "suggestion": f"You haven't checked in with {d.canonical_name} in {days_elapsed} days (target: {d.touchpoint_cadence_days} days)."
                        })
                except Exception:
                    pass
                    
        return alerts
