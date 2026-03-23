"""
Dione AI — Relationship Types for the Knowledge Graph

Defines the types of edges (relationships) between entities.
This is what makes the knowledge graph powerful — it's not just
storing data, it's storing *connections* between data.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class RelationType(Enum):
    """Types of relationships between entities."""
    
    # Person relationships
    KNOWS = "knows"                     # Person <-> Person
    WORKS_WITH = "works_with"           # Person <-> Person
    MANAGES = "manages"                 # Person -> Person
    REPORTS_TO = "reports_to"           # Person -> Person
    FRIEND_OF = "friend_of"            # Person <-> Person
    FAMILY_OF = "family_of"            # Person <-> Person
    
    # Person <-> Entity
    SENT = "sent"                       # Person -> Document/Message
    RECEIVED = "received"               # Person -> Document/Message
    CREATED = "created"                 # Person -> Document/Project
    ASSIGNED_TO = "assigned_to"         # Task -> Person
    PARTICIPANT_IN = "participant_in"   # Person -> Event
    MEMBER_OF = "member_of"            # Person -> Organization
    
    # Document relationships
    ATTACHED_TO = "attached_to"         # Document -> Message/Email
    ABOUT = "about"                     # Document -> Topic
    RELATED_TO = "related_to"          # Any <-> Any (generic relation)
    
    # Event relationships
    SCHEDULED_FOR = "scheduled_for"     # Event -> datetime
    LOCATED_AT = "located_at"          # Event -> Location
    
    # Task relationships
    PART_OF = "part_of"                # Task -> Project
    DEPENDS_ON = "depends_on"          # Task -> Task
    BLOCKED_BY = "blocked_by"          # Task -> Task
    
    # Communication
    MENTIONED_IN = "mentioned_in"      # Entity -> Message/Document
    DISCUSSED = "discussed"            # Topic mentioned in conversation


@dataclass
class Relation:
    """An edge in the knowledge graph connecting two entities."""
    id: str
    source_id: str          # Entity ID
    target_id: str          # Entity ID
    relation_type: RelationType
    weight: float = 1.0     # Strength of the relationship (0-1)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    # Context about when/how this relation was discovered
    context: Optional[str] = None  # e.g., "Mentioned in email from Alice on 2026-02-15"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Relation":
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data["relation_type"]),
            weight=data.get("weight", 1.0),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata", {}),
            context=data.get("context"),
        )
