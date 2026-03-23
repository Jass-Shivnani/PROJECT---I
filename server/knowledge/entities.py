"""
Dione AI — Entity Definitions for the Knowledge Graph

Defines the types of entities (nodes) that exist in the user's
personal knowledge graph: People, Events, Documents, Projects, etc.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class EntityType(Enum):
    """Types of entities in the knowledge graph."""
    PERSON = "person"
    EVENT = "event"
    DOCUMENT = "document"
    PROJECT = "project"
    LOCATION = "location"
    ORGANIZATION = "organization"
    TOPIC = "topic"
    APPLICATION = "application"  # Software/app the user uses
    MESSAGE = "message"
    TASK = "task"


@dataclass
class Entity:
    """Base entity in the knowledge graph."""
    id: str
    type: EntityType
    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)
    
    # Embedding vector for semantic search
    embedding: Optional[list[float]] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        return cls(
            id=data["id"],
            type=EntityType(data["type"]),
            name=data["name"],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PersonEntity(Entity):
    """A person in the user's network."""
    email: Optional[str] = None
    phone: Optional[str] = None
    relationship: Optional[str] = None  # e.g., "colleague", "friend", "manager"
    
    def __post_init__(self):
        self.type = EntityType.PERSON


@dataclass
class EventEntity(Entity):
    """A calendar event or meeting."""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    participants: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = EntityType.EVENT


@dataclass
class DocumentEntity(Entity):
    """A document, file, or attachment."""
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    source: Optional[str] = None  # "whatsapp", "email", "local"
    summary: Optional[str] = None

    def __post_init__(self):
        self.type = EntityType.DOCUMENT


@dataclass
class TaskEntity(Entity):
    """A task or to-do item."""
    status: str = "pending"  # pending, in_progress, done
    priority: str = "medium"  # low, medium, high, urgent
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None

    def __post_init__(self):
        self.type = EntityType.TASK
