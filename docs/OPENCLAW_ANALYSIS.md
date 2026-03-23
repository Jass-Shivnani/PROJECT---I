# OpenClaw Architecture Analysis — Applied to Dione AI

## Executive Summary

OpenClaw is an open-source personal AI assistant that connects to 20+ messaging channels through a unified Gateway and executes tasks via a plugin-powered agent runtime. It's built in TypeScript/Node.js with a sophisticated plugin system, hook lifecycle, and security model.

**Key numbers:** 38 plugins, 26 lifecycle hooks, 52 bundled skills, 22 channel integrations, Zod-validated config, Docker sandboxing.

---

## What Dione Should Adopt (Adapted for Python/FastAPI + Flutter)

### 1. Plugin Architecture — Registry + Factory Pattern

**OpenClaw approach:** Plugins export `register(api)` which receives an `OpenClawPluginApi` object with typed registration methods. A central `PluginRegistry` accumulates all registrations.

**Dione adaptation:**
```python
class DionePluginApi:
    def register_tool(self, tool: Tool) -> None
    def register_hook(self, event: str, handler: Callable) -> None
    def register_service(self, service: BackgroundService) -> None
    def register_layout(self, layout: LayoutTemplate) -> None  # NEW for Dione
    def register_integration(self, integration: Integration) -> None  # NEW
    def register_command(self, name: str, handler: Callable) -> None

class DionePlugin(ABC):
    id: str
    name: str
    version: str
    config_schema: dict  # Pydantic model → JSON Schema
    permissions: list[Permission]
    
    @abstractmethod
    async def register(self, api: DionePluginApi) -> None
    
    async def activate(self, api: DionePluginApi) -> None  # Optional
    async def deactivate(self) -> None  # Optional
```

### 2. Hook Lifecycle System — 20+ Typed Hooks

**OpenClaw approach:** 26 named hooks with typed events, priority ordering, and merge strategies. Void hooks run in parallel, result hooks run sequentially.

**Dione hooks to implement:**
| Hook | Phase | Description |
|------|-------|-------------|
| `before_chat` | Pre-LLM | Modify/augment prompt before sending |
| `after_chat` | Post-LLM | Process response before delivering to user |
| `before_tool_call` | Tool | Inspect/block/modify tool call params |
| `after_tool_call` | Tool | Process tool results |
| `on_mood_change` | Personality | React to mood shifts |
| `on_pattern_detected` | Layout | Trigger layout changes |
| `on_layout_change` | Layout | Layout is being switched |
| `before_memory_save` | Memory | Before saving to long-term memory |
| `after_memory_recall` | Memory | After retrieving from memory |
| `on_integration_event` | Integration | External service event received |
| `on_user_profile_update` | Profile | User profile data changed |
| `on_session_start` | Session | New conversation started |
| `on_session_end` | Session | Conversation ended |
| `on_plugin_loaded` | System | Plugin successfully loaded |
| `on_heartbeat` | Proactive | Periodic heartbeat check |

### 3. Permission-Based Safeguards

**OpenClaw approach:** Tool allow/deny lists, exec approval workflows, DM policies, security audit CLI, Docker sandboxing.

**Dione adaptation:**
```python
class Permission(Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    NETWORK_ACCESS = "network_access"
    SYSTEM_COMMANDS = "system_commands"
    GOOGLE_DRIVE = "google_drive"
    GOOGLE_PHOTOS = "google_photos"
    GOOGLE_MAIL = "google_mail"
    GOOGLE_CALENDAR = "google_calendar"
    BROWSER_ACCESS = "browser_access"
    CAMERA_ACCESS = "camera_access"
    LOCATION_ACCESS = "location_access"
    CONTACTS_ACCESS = "contacts_access"

class PermissionManager:
    def grant(self, plugin_id: str, permission: Permission) -> None
    def revoke(self, plugin_id: str, permission: Permission) -> None
    def check(self, plugin_id: str, permission: Permission) -> bool
    def request(self, plugin_id: str, permission: Permission) -> PermissionRequest
    def audit_log(self) -> list[PermissionAuditEntry]
```

### 4. Integration System — Channel Adapter Pattern

**OpenClaw approach:** 22 channel adapters all implementing a common interface, normalized message format.

**Dione adaptation (integrations instead of channels):**
```python
class Integration(ABC):
    id: str
    name: str
    icon: str
    auth_type: AuthType  # oauth2, api_key, token, device_code
    required_permissions: list[Permission]
    config_schema: dict
    
    @abstractmethod
    async def connect(self, credentials: dict) -> bool
    
    @abstractmethod
    async def disconnect(self) -> None
    
    @abstractmethod
    async def get_tools(self) -> list[Tool]
    
    @abstractmethod
    async def get_layouts(self) -> list[LayoutTemplate]  # NEW
```

### 5. Skill System — Markdown Prompt Injection

**OpenClaw approach:** Skills are `SKILL.md` files with YAML frontmatter + markdown instructions. They're injected into the LLM system prompt, NOT executed as code.

**Dione adaptation:** Same concept — skills as `.md` files that teach the LLM how to use specific tools or handle specific domains.

### 6. Config System — Pydantic Validated

**OpenClaw approach:** Zod schemas compiled to JSON Schema. Plugin configs merged into global tree.

**Dione adaptation:** Pydantic models with `model_json_schema()` for each plugin. Global config at `~/.dione/config.json`.

---

## Dione Plugin Categories

### Core Plugins (Built-in)
| Plugin | Purpose |
|--------|---------|
| `system` | File system, date/time, clipboard, system info |
| `web` | Web search, fetch, scrape |
| `code` | Code execution, analysis, formatting |
| `memory` | Short-term + long-term memory (exclusive slot) |
| `personality` | Mood engine, user profiling |
| `layout` | Adaptive layout engine |

### Integration Plugins (User-enabled)
| Plugin | Purpose | Permissions | Layout |
|--------|---------|-------------|--------|
| `google-drive` | File storage, docs, sheets | GOOGLE_DRIVE | File manager |
| `google-photos` | Photo library, memories | GOOGLE_PHOTOS | Photo gallery / Memories |
| `google-mail` | Email read/send/search | GOOGLE_MAIL | Email client |
| `google-calendar` | Events, scheduling | GOOGLE_CALENDAR | Calendar view |
| `spotify` | Music playback, playlists | NETWORK_ACCESS | Media player |
| `github` | Repos, issues, PRs | NETWORK_ACCESS | Code workspace |
| `notion` | Notes, databases | NETWORK_ACCESS | Note-taking layout |
| `twitter/x` | Social feed, posts | NETWORK_ACCESS | Social feed |
| `reddit` | Subreddits, posts | NETWORK_ACCESS | Content reader |
| `news-api` | News articles | NETWORK_ACCESS | News reader |
| `weather` | Weather data | NETWORK_ACCESS | Weather widget |
| `fitness` | Health data | LOCATION_ACCESS | Health dashboard |
| `finance` | Stocks, crypto, budgets | NETWORK_ACCESS | Finance dashboard |
| `trello` | Task boards | NETWORK_ACCESS | Kanban board |
| `todoist` | Todo lists | NETWORK_ACCESS | Task manager |

### Layout-Generating Plugins
Each integration can register layout templates. When the AI detects usage patterns, it activates the appropriate layout:

| Pattern Detected | Layout Activated | Source Plugin |
|-----------------|------------------|---------------|
| User asks about news daily | News Reader layout | `news-api` |
| User manages code projects | Code Workspace layout | `github` |
| User checks calendar often | Calendar layout | `google-calendar` |
| User reads many emails | Email Client layout | `google-mail` |
| User track tasks/todos | Kanban Board layout | `trello`/`todoist` |
| User asks about stocks | Finance Dashboard | `finance` |
| User discusses music | Media Player layout | `spotify` |

---

## Adaptive Layout Architecture

### Server-Side Layout Engine
```python
class LayoutEngine:
    templates: dict[str, LayoutTemplate]  # All registered templates
    active_layout: str  # Currently active layout ID
    workspaces: list[Workspace]  # Saved workspaces
    
    def detect_pattern(self, chat_history: list) -> str | None
    def get_layout_schema(self, layout_id: str) -> dict  # JSON schema
    def switch_layout(self, layout_id: str) -> LayoutDirective
    def customize_section(self, layout_id: str, section_id: str, changes: dict) -> None
```

### Layout Template Schema
```json
{
  "id": "news_reader",
  "name": "News Feed",
  "description": "Optimized for reading news and articles",
  "icon": "newspaper",
  "trigger_patterns": ["news", "article", "headline", "technology news"],
  "sections": [
    {
      "id": "header",
      "type": "app_bar",
      "components": [
        { "type": "search_bar", "placeholder": "Search news..." },
        { "type": "category_tabs", "items": ["AI", "Web", "Mobile", "Cloud"] }
      ]
    },
    {
      "id": "featured",
      "type": "carousel",
      "data_source": "top_stories",
      "component": { "type": "featured_card", "style": "hero" }
    },
    {
      "id": "feed",
      "type": "list",
      "data_source": "articles",
      "component": { "type": "article_card", "style": "compact" },
      "infinite_scroll": true
    },
    {
      "id": "chat_fab",
      "type": "floating_action_button",
      "icon": "chat",
      "action": "open_chat"
    }
  ],
  "theme_overrides": {
    "primary": "#1565C0",
    "surface": "#FAFAFA",
    "card_style": "elevated"
  }
}
```

### Flutter Layout Renderer
```dart
class AdaptiveLayoutRenderer extends StatelessWidget {
  final LayoutSchema schema;
  final Map<String, dynamic> data;
  
  Widget build(BuildContext context) {
    return switch (schema.type) {
      'news_reader' => NewsReaderLayout(schema, data),
      'code_workspace' => CodeWorkspaceLayout(schema, data),
      'task_board' => TaskBoardLayout(schema, data),
      'calendar' => CalendarLayout(schema, data),
      'finance_dashboard' => FinanceDashboardLayout(schema, data),
      'media_player' => MediaPlayerLayout(schema, data),
      'email_client' => EmailClientLayout(schema, data),
      _ => DefaultChatLayout(schema, data),
    };
  }
}
```

---

## Memory & "On This Day" System

### Memories Plugin
Inspired by Google Photos "On this day":

```python
class MemoryPlugin:
    def save_memory(self, event: MemoryEvent) -> None
    def recall(self, query: str) -> list[Memory]
    def get_on_this_day(self, date: date) -> list[Memory]
    def get_milestones(self) -> list[Memory]
    def get_weekly_recap(self) -> WeeklyRecap
    
class MemoryEvent:
    timestamp: datetime
    type: str  # "conversation", "achievement", "discovery", "milestone"
    content: str
    metadata: dict  # tool used, mood, layout active, etc.
    tags: list[str]
    sentiment: float
    importance: float  # AI-scored 0-1
```

Memories are surfaced:
- In the "On This Day" card on home screen
- As proactive suggestions ("Remember when you...")
- In weekly/monthly recap layouts
- As context for personalization

---

## Implementation Priority

### Phase 1: Plugin System Foundation
1. `PluginApi`, `PluginRegistry`, `PluginLoader`
2. `PermissionManager` with grant/revoke/check
3. `HookRunner` with priority + merge strategies
4. Plugin manifest validation (Pydantic)
5. 3 core plugins: `system`, `web`, `memory`

### Phase 2: Integration Framework
1. `Integration` base class with OAuth2 flow
2. Google Auth setup (OAuth2 client)
3. `google-drive` plugin
4. `google-photos` plugin with Memories
5. `google-mail` plugin

### Phase 3: Adaptive Layout System
1. `LayoutEngine` with pattern detection
2. Layout schema system (JSON templates)
3. Flutter `AdaptiveLayoutRenderer`
4. 5 initial layouts: Chat, News, Code, Tasks, Calendar
5. Workspace save/load

### Phase 4: Full Integration Suite
1. More Google services (Calendar, Keep, Maps)
2. Third-party integrations (Spotify, GitHub, Notion)
3. 15+ layout templates
4. "On This Day" memory system
5. Weekly recap proactive agent
