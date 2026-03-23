"""
Dione AI — Plugin System v2: Types & Contracts

Core type definitions for the plugin architecture, inspired by
OpenClaw's registry + factory + hook pattern, adapted for Python/FastAPI.

This module defines:
  - Permission system enums and dataclasses
  - Hook system types (events, handlers, merge strategies)
  - Plugin API interface
  - Integration base types
  - Layout schema types
  - Memory types
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Optional, Protocol, Union,
    TYPE_CHECKING
)
from datetime import datetime


# ─── Permission System ────────────────────────────────────────

class Permission(enum.Enum):
    """All grantable permissions in Dione."""
    # Core
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    NETWORK_ACCESS = "network_access"
    SYSTEM_COMMANDS = "system_commands"
    
    # Google Services
    GOOGLE_DRIVE = "google_drive"
    GOOGLE_PHOTOS = "google_photos"
    GOOGLE_MAIL = "google_mail"
    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_CONTACTS = "google_contacts"
    GOOGLE_KEEP = "google_keep"
    
    # Device / Phone
    CAMERA_ACCESS = "camera_access"
    LOCATION_ACCESS = "location_access"
    CONTACTS_ACCESS = "contacts_access"
    NOTIFICATIONS = "notifications"
    MICROPHONE = "microphone"
    CLIPBOARD = "clipboard"
    
    # Third-party
    GITHUB_ACCESS = "github_access"
    SPOTIFY_ACCESS = "spotify_access"
    NOTION_ACCESS = "notion_access"
    TWITTER_ACCESS = "twitter_access"
    REDDIT_ACCESS = "reddit_access"
    
    # Dangerous
    BROWSER_CONTROL = "browser_control"
    BACKGROUND_EXECUTION = "background_execution"


class PermissionLevel(enum.Enum):
    """Risk tiers for permissions."""
    SAFE = "safe"            # Read-only, no external access
    MODERATE = "moderate"    # Network, read external
    SENSITIVE = "sensitive"  # Write external, PII access
    DANGEROUS = "dangerous"  # System commands, browser control


PERMISSION_LEVELS: dict[Permission, PermissionLevel] = {
    Permission.READ_FILES: PermissionLevel.SAFE,
    Permission.CLIPBOARD: PermissionLevel.SAFE,
    Permission.WRITE_FILES: PermissionLevel.MODERATE,
    Permission.NETWORK_ACCESS: PermissionLevel.MODERATE,
    Permission.GOOGLE_DRIVE: PermissionLevel.SENSITIVE,
    Permission.GOOGLE_PHOTOS: PermissionLevel.SENSITIVE,
    Permission.GOOGLE_MAIL: PermissionLevel.SENSITIVE,
    Permission.GOOGLE_CALENDAR: PermissionLevel.SENSITIVE,
    Permission.GOOGLE_CONTACTS: PermissionLevel.SENSITIVE,
    Permission.GOOGLE_KEEP: PermissionLevel.MODERATE,
    Permission.CAMERA_ACCESS: PermissionLevel.SENSITIVE,
    Permission.LOCATION_ACCESS: PermissionLevel.SENSITIVE,
    Permission.CONTACTS_ACCESS: PermissionLevel.SENSITIVE,
    Permission.NOTIFICATIONS: PermissionLevel.MODERATE,
    Permission.MICROPHONE: PermissionLevel.SENSITIVE,
    Permission.GITHUB_ACCESS: PermissionLevel.MODERATE,
    Permission.SPOTIFY_ACCESS: PermissionLevel.SAFE,
    Permission.NOTION_ACCESS: PermissionLevel.MODERATE,
    Permission.TWITTER_ACCESS: PermissionLevel.MODERATE,
    Permission.REDDIT_ACCESS: PermissionLevel.SAFE,
    Permission.SYSTEM_COMMANDS: PermissionLevel.DANGEROUS,
    Permission.BROWSER_CONTROL: PermissionLevel.DANGEROUS,
    Permission.BACKGROUND_EXECUTION: PermissionLevel.DANGEROUS,
}


@dataclass
class PermissionGrant:
    """A record of a permission grant/revoke."""
    plugin_id: str
    permission: Permission
    granted: bool
    granted_at: datetime
    granted_by: str = "user"  # "user" | "system" | "auto"
    expires_at: Optional[datetime] = None
    reason: str = ""


@dataclass
class PermissionAuditEntry:
    """An entry in the permission audit log."""
    timestamp: datetime
    plugin_id: str
    permission: Permission
    action: str  # "check" | "grant" | "revoke" | "denied"
    result: bool
    context: str = ""


# ─── Hook System ──────────────────────────────────────────────

class HookEvent(enum.Enum):
    """All lifecycle hooks in Dione."""
    # Chat lifecycle
    BEFORE_CHAT = "before_chat"
    AFTER_CHAT = "after_chat"
    
    # Tool lifecycle
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    
    # Personality / Mood
    ON_MOOD_CHANGE = "on_mood_change"
    
    # Layout / UI
    ON_PATTERN_DETECTED = "on_pattern_detected"
    ON_LAYOUT_CHANGE = "on_layout_change"
    
    # Memory
    BEFORE_MEMORY_SAVE = "before_memory_save"
    AFTER_MEMORY_RECALL = "after_memory_recall"
    
    # Integration
    ON_INTEGRATION_CONNECT = "on_integration_connect"
    ON_INTEGRATION_DISCONNECT = "on_integration_disconnect"
    ON_INTEGRATION_EVENT = "on_integration_event"
    
    # User & Session
    ON_USER_PROFILE_UPDATE = "on_user_profile_update"
    ON_SESSION_START = "on_session_start"
    ON_SESSION_END = "on_session_end"
    
    # System
    ON_PLUGIN_LOADED = "on_plugin_loaded"
    ON_PLUGIN_UNLOADED = "on_plugin_unloaded"
    ON_HEARTBEAT = "on_heartbeat"
    ON_SERVER_START = "on_server_start"
    ON_SERVER_STOP = "on_server_stop"


@dataclass
class HookContext:
    """Base context passed to all hook handlers."""
    event: HookEvent
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    plugin_id: Optional[str] = None  # Which plugin triggered this
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatHookContext(HookContext):
    """Context for chat hooks (before_chat, after_chat)."""
    message: str = ""
    response: str = ""
    mood: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    ui_directives: dict = field(default_factory=dict)


@dataclass
class ToolHookContext(HookContext):
    """Context for tool hooks."""
    tool_name: str = ""
    tool_params: dict = field(default_factory=dict)
    tool_result: Any = None
    duration_ms: float = 0.0
    blocked: bool = False
    block_reason: str = ""


@dataclass
class MoodHookContext(HookContext):
    """Context for mood change hooks."""
    old_mood: str = ""
    new_mood: str = ""
    old_state: dict = field(default_factory=dict)
    new_state: dict = field(default_factory=dict)


@dataclass
class LayoutHookContext(HookContext):
    """Context for layout hooks."""
    pattern_type: str = ""   # "news", "code", "tasks", etc.
    confidence: float = 0.0
    old_layout: str = ""
    new_layout: str = ""
    layout_schema: dict = field(default_factory=dict)


@dataclass
class IntegrationHookContext(HookContext):
    """Context for integration hooks."""
    integration_id: str = ""
    integration_name: str = ""
    event_type: str = ""
    event_data: dict = field(default_factory=dict)


@dataclass
class MemoryHookContext(HookContext):
    """Context for memory hooks."""
    memory_type: str = ""
    content: str = ""
    importance: float = 0.0
    tags: list[str] = field(default_factory=list)


class MergeStrategy(enum.Enum):
    """How multiple hook results are combined."""
    FIRST_WINS = "first_wins"           # First non-None result wins
    LAST_WINS = "last_wins"             # Last non-None result wins
    CONCATENATE = "concatenate"         # Concatenate all string results
    MERGE_DICTS = "merge_dicts"         # Deep merge all dict results
    ANY_BLOCKS = "any_blocks"           # If any handler returns block=True
    ALL_RESULTS = "all_results"         # Return list of all results


# Map hooks to their merge strategy
HOOK_MERGE_STRATEGIES: dict[HookEvent, MergeStrategy] = {
    HookEvent.BEFORE_CHAT: MergeStrategy.MERGE_DICTS,
    HookEvent.AFTER_CHAT: MergeStrategy.MERGE_DICTS,
    HookEvent.BEFORE_TOOL_CALL: MergeStrategy.ANY_BLOCKS,
    HookEvent.AFTER_TOOL_CALL: MergeStrategy.LAST_WINS,
    HookEvent.ON_MOOD_CHANGE: MergeStrategy.ALL_RESULTS,
    HookEvent.ON_PATTERN_DETECTED: MergeStrategy.FIRST_WINS,
    HookEvent.ON_LAYOUT_CHANGE: MergeStrategy.ALL_RESULTS,
    HookEvent.BEFORE_MEMORY_SAVE: MergeStrategy.ANY_BLOCKS,
    HookEvent.AFTER_MEMORY_RECALL: MergeStrategy.MERGE_DICTS,
    HookEvent.ON_INTEGRATION_EVENT: MergeStrategy.ALL_RESULTS,
    HookEvent.ON_USER_PROFILE_UPDATE: MergeStrategy.ALL_RESULTS,
    HookEvent.ON_HEARTBEAT: MergeStrategy.ALL_RESULTS,
}


@dataclass
class HookRegistration:
    """A registered hook handler."""
    event: HookEvent
    handler: Callable
    plugin_id: str
    priority: int = 100      # Lower = runs first
    enabled: bool = True


# ─── Integration Types ────────────────────────────────────────

class AuthType(enum.Enum):
    """Authentication methods for integrations."""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    TOKEN = "token"
    DEVICE_CODE = "device_code"
    NONE = "none"


class IntegrationStatus(enum.Enum):
    """Connection status of an integration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    EXPIRED = "expired"


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""
    id: str
    name: str
    icon: str = ""
    description: str = ""
    auth_type: AuthType = AuthType.NONE
    required_permissions: list[Permission] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)  # JSON Schema
    oauth_scopes: list[str] = field(default_factory=list)
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_auth_url: str = ""
    oauth_token_url: str = ""
    oauth_redirect_uri: str = ""


@dataclass
class IntegrationCredentials:
    """Stored credentials for an integration."""
    integration_id: str
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    api_key: str = ""
    extra: dict = field(default_factory=dict)


# ─── Layout Types ─────────────────────────────────────────────

class LayoutType(enum.Enum):
    """Core layout categories."""
    CHAT = "chat"                       # Default conversational
    CONTENT_READER = "content_reader"   # News, articles, blogs
    CODE_WORKSPACE = "code_workspace"   # Developer tools
    TASK_BOARD = "task_board"           # Kanban, todos, calendar
    LEARNING_HUB = "learning_hub"      # Study, flashcards, quiz
    DASHBOARD = "dashboard"            # Charts, stats, KPIs
    MEDIA_CENTER = "media_center"      # Music, video, player
    SOCIAL_FEED = "social_feed"        # Social media style
    EMAIL_CLIENT = "email_client"      # Mail inbox
    CALENDAR = "calendar"              # Schedule, events
    FILE_MANAGER = "file_manager"      # Drive, files, docs
    PHOTO_GALLERY = "photo_gallery"    # Photos, memories
    JOURNAL = "journal"                # Diary, reflective
    HEALTH_TRACKER = "health_tracker"  # Fitness, nutrition
    FINANCE = "finance"                # Stocks, budget
    TRAVEL = "travel"                  # Itinerary, maps
    CUSTOM = "custom"                  # AI-generated


@dataclass
class LayoutSection:
    """A section within a layout."""
    id: str
    type: str  # "header", "body", "sidebar", "footer", "fab", "modal"
    arrangement: str = "vertical"  # "vertical", "horizontal", "grid", "kanban", "carousel"
    components: list[dict] = field(default_factory=list)
    data_source: str = ""
    style: dict = field(default_factory=dict)
    visible: bool = True
    order: int = 0


@dataclass
class LayoutTemplate:
    """A complete layout template that the app can render."""
    id: str
    name: str
    description: str
    type: LayoutType
    icon: str = ""
    plugin_id: str = ""             # Which plugin registered this
    trigger_patterns: list[str] = field(default_factory=list)
    trigger_keywords: list[str] = field(default_factory=list)
    min_confidence: float = 0.7
    sections: list[LayoutSection] = field(default_factory=list)
    theme_overrides: dict = field(default_factory=dict)
    data_requirements: list[str] = field(default_factory=list)  # Required integrations
    is_customizable: bool = True
    
    def to_schema(self) -> dict:
        """Serialize to JSON schema for the Flutter client."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "icon": self.icon,
            "sections": [
                {
                    "id": s.id,
                    "type": s.type,
                    "arrangement": s.arrangement,
                    "components": s.components,
                    "data_source": s.data_source,
                    "style": s.style,
                    "visible": s.visible,
                    "order": s.order,
                }
                for s in self.sections
            ],
            "theme_overrides": self.theme_overrides,
        }


@dataclass
class Workspace:
    """A saved workspace (layout + config + data)."""
    id: str
    name: str
    layout_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    layout_customizations: dict = field(default_factory=dict)
    pinned_tools: list[str] = field(default_factory=list)
    data_cache: dict = field(default_factory=dict)
    is_auto_generated: bool = False


# ─── Memory Types ─────────────────────────────────────────────

class MemoryType(enum.Enum):
    """Types of memories Dione can store."""
    CONVERSATION = "conversation"     # Chat interaction
    FACT = "fact"                      # Learned fact about user
    PREFERENCE = "preference"         # User preference
    ACHIEVEMENT = "achievement"       # User milestone
    DISCOVERY = "discovery"           # Something the user learned
    ROUTINE = "routine"               # Detected routine/habit
    RELATIONSHIP = "relationship"     # Connection between entities
    INTEGRATION_EVENT = "event"       # External service event
    EMOTION = "emotion"               # Emotional moment
    MILESTONE = "milestone"           # Significant event


@dataclass
class Memory:
    """A single memory entry."""
    id: str
    type: MemoryType
    content: str
    summary: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5     # 0.0 = trivial, 1.0 = critical
    sentiment: float = 0.0     # -1.0 = negative, 1.0 = positive
    tags: list[str] = field(default_factory=list)
    source_plugin: str = ""
    source_integration: str = ""
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    recalled_count: int = 0
    last_recalled: Optional[datetime] = None


@dataclass
class WeeklyRecap:
    """A weekly summary of activities, memories, and patterns."""
    week_start: datetime
    week_end: datetime
    top_memories: list[Memory] = field(default_factory=list)
    mood_summary: dict = field(default_factory=dict)
    tools_used: dict[str, int] = field(default_factory=dict)
    topics_discussed: list[str] = field(default_factory=list)
    patterns_detected: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


# ─── Plugin State ─────────────────────────────────────────────

class PluginStatus(enum.Enum):
    """Runtime status of a plugin."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginManifest:
    """
    Plugin metadata — validated before any code executes.
    Equivalent to OpenClaw's openclaw.plugin.json.
    """
    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    icon: str = ""
    
    # Classification
    kind: str = "tool"  # "tool" | "integration" | "layout" | "memory" | "service"
    exclusive_slot: Optional[str] = None  # e.g., "memory" — only one active
    
    # Requirements
    required_permissions: list[Permission] = field(default_factory=list)
    required_integrations: list[str] = field(default_factory=list)
    required_plugins: list[str] = field(default_factory=list)
    
    # Config
    config_schema: dict = field(default_factory=dict)  # JSON Schema
    default_config: dict = field(default_factory=dict)
    
    # What this plugin provides
    provides_tools: bool = False
    provides_hooks: bool = False
    provides_layouts: bool = False
    provides_integration: bool = False
    provides_service: bool = False
    provides_commands: bool = False
    
    # Safety
    is_builtin: bool = False
    is_trusted: bool = False
    risk_level: PermissionLevel = PermissionLevel.SAFE
