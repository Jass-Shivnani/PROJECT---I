"""
Dione AI — Dynamic UI Component System

The AI controls the entire user interface experience.
Instead of fixed layouts, Dione generates UI components
that the Flutter app renders dynamically.

This gives Dione the ability to:
- Change the theme based on mood/time
- Show proactive cards (suggestions, reminders)
- Customize the chat interface per user
- Display data visualizations
- Create interactive action panels
- Alter its own avatar expression
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from enum import Enum


class ComponentType(Enum):
    """All UI component types the Flutter app can render."""
    # Chat-level components
    CHAT_BUBBLE = "chat_bubble"         # Standard message bubble
    RICH_CARD = "rich_card"             # Card with title, body, image, actions
    ACTION_PANEL = "action_panel"       # Grid of quick-action buttons
    CODE_BLOCK = "code_block"           # Syntax-highlighted code
    DATA_TABLE = "data_table"           # Structured data table
    CHART = "chart"                     # Simple chart (bar, line, pie)
    FILE_PREVIEW = "file_preview"       # File content preview
    SYSTEM_STATS = "system_stats"       # CPU/RAM/Disk gauges
    
    # Full-screen / overlay components
    MORNING_SUMMARY = "morning_summary"  # Morning briefing card
    DAILY_RECAP = "daily_recap"          # Evening summary
    CONFIRMATION = "confirmation"        # "Are you sure?" dialog
    
    # Ambient / background components
    MOOD_INDICATOR = "mood_indicator"    # Dione's current mood visualization
    AVATAR_EXPRESSION = "avatar"         # Dione's avatar state/expression
    THEME_DIRECTIVE = "theme_directive"  # Change app theme/colors
    AMBIENT_ANIMATION = "ambient"        # Background animation state
    
    # Proactive components
    SUGGESTION_CARD = "suggestion_card"  # Proactive suggestion
    REMINDER = "reminder"                # Timed reminder
    HABIT_CARD = "habit_card"            # Pattern-based suggestion
    NOTIFICATION = "notification"        # Toast notification


@dataclass
class UIAction:
    """An interactive action button in a UI component."""
    label: str
    action_type: str      # "confirm", "dismiss", "snooze", "execute", "navigate"
    payload: dict = field(default_factory=dict)
    style: str = "default"  # "default", "primary", "danger", "outline"


@dataclass
class UIComponent:
    """
    A single UI component that the AI generates.
    
    The Flutter app receives these and renders them dynamically.
    """
    component_type: str           # One of ComponentType values
    data: dict = field(default_factory=dict)
    actions: list[UIAction] = field(default_factory=list)
    style: dict = field(default_factory=dict)
    # style can contain: {"variant": "...", "color": "#...", "elevation": 2, etc.}
    priority: int = 0             # Higher = more prominent placement
    ttl_seconds: Optional[int] = None  # Auto-remove after N seconds

    def to_dict(self) -> dict:
        return {
            "type": self.component_type,
            "data": self.data,
            "actions": [asdict(a) for a in self.actions],
            "style": self.style,
            "priority": self.priority,
            "ttl_seconds": self.ttl_seconds,
        }


@dataclass
class ThemeDirective:
    """
    Tells the Flutter app how to theme itself.
    
    Dione decides the visual atmosphere based on:
    - Current mood
    - Time of day
    - User's profession/preferences
    - Conversation context
    """
    primary_color: str = "#6C63FF"      # Default purple
    secondary_color: str = "#FF6584"
    background_mode: str = "default"     # "default", "dark", "warm", "cool", "focus"
    accent_animation: str = "none"       # "none", "pulse", "breathe", "particles", "aurora"
    avatar_expression: str = "neutral"   # "neutral", "happy", "thinking", "concerned", "excited"
    chat_bubble_style: str = "default"   # "default", "minimal", "rounded", "glassmorphic"
    font_weight: str = "normal"          # "light", "normal", "medium"
    
    def to_dict(self) -> dict:
        return asdict(self)


class UIDirectiveBuilder:
    """
    Generates UI directives based on context.
    
    Called by the engine after each response to determine
    what UI changes should accompany the message.
    """

    # Profession → default theme mappings
    PROFESSION_THEMES = {
        "doctor": {
            "primary_color": "#2196F3",
            "secondary_color": "#4CAF50",
            "background_mode": "cool",
            "chat_bubble_style": "minimal",
            "font_weight": "normal",
        },
        "developer": {
            "primary_color": "#6C63FF",
            "secondary_color": "#00BCD4",
            "background_mode": "dark",
            "chat_bubble_style": "glassmorphic",
            "font_weight": "normal",
        },
        "designer": {
            "primary_color": "#E91E63",
            "secondary_color": "#FF9800",
            "background_mode": "warm",
            "chat_bubble_style": "rounded",
            "font_weight": "light",
        },
        "student": {
            "primary_color": "#4CAF50",
            "secondary_color": "#FFC107",
            "background_mode": "default",
            "chat_bubble_style": "rounded",
            "font_weight": "normal",
        },
        "finance": {
            "primary_color": "#1B5E20",
            "secondary_color": "#FFD700",
            "background_mode": "dark",
            "chat_bubble_style": "minimal",
            "font_weight": "medium",
        },
    }

    # Mood → avatar expression mapping
    MOOD_AVATARS = {
        "enthusiastic": "excited",
        "calm": "neutral",
        "cheerful": "happy",
        "focused": "thinking",
        "curious": "thinking",
        "professional": "neutral",
        "playful": "happy",
        "balanced": "neutral",
    }

    # Mood → ambient animation
    MOOD_ANIMATIONS = {
        "enthusiastic": "particles",
        "calm": "breathe",
        "cheerful": "aurora",
        "focused": "none",
        "curious": "pulse",
        "professional": "none",
        "playful": "particles",
        "balanced": "breathe",
    }

    def build_theme(self, mood_label: str, profession: str = "unknown",
                    hour: int = -1) -> ThemeDirective:
        """Build a complete theme directive."""
        import time as _time
        if hour < 0:
            hour = int(_time.strftime("%H"))

        theme = ThemeDirective()

        # Apply profession theme
        if profession in self.PROFESSION_THEMES:
            for key, value in self.PROFESSION_THEMES[profession].items():
                setattr(theme, key, value)

        # Time-of-day background override
        if hour >= 21 or hour < 6:
            theme.background_mode = "dark"
        elif 6 <= hour < 10:
            if theme.background_mode == "default":
                theme.background_mode = "warm"

        # Mood-driven avatar and animation
        theme.avatar_expression = self.MOOD_AVATARS.get(mood_label, "neutral")
        theme.accent_animation = self.MOOD_ANIMATIONS.get(mood_label, "breathe")

        return theme

    def build_response_components(
        self,
        response_text: str,
        tools_used: list[str],
        mood_label: str,
        has_code: bool = False,
        system_stats: Optional[dict] = None,
    ) -> list[UIComponent]:
        """
        Generate UI components to accompany a chat response.
        
        The AI doesn't just send text — it sends a complete
        visual experience.
        """
        components = []

        # Main chat bubble (always present)
        components.append(UIComponent(
            component_type=ComponentType.CHAT_BUBBLE.value,
            data={"text": response_text},
            style={"mood": mood_label},
        ))

        # Mood indicator
        components.append(UIComponent(
            component_type=ComponentType.MOOD_INDICATOR.value,
            data={"mood": mood_label},
            style={"size": "small"},
            priority=-1,  # Background element
        ))

        # Code block extraction
        if has_code or "```" in response_text:
            import re
            code_blocks = re.findall(r"```(\w*)\n(.*?)```", response_text, re.DOTALL)
            for lang, code in code_blocks:
                components.append(UIComponent(
                    component_type=ComponentType.CODE_BLOCK.value,
                    data={"language": lang or "text", "code": code.strip()},
                    priority=1,
                ))

        # System stats card if system tool was used
        if system_stats or any("system_info" in t for t in tools_used):
            if system_stats:
                components.append(UIComponent(
                    component_type=ComponentType.SYSTEM_STATS.value,
                    data=system_stats,
                    style={"variant": "gauge"},
                    priority=2,
                ))

        # Quick actions based on context
        if tools_used:
            actions = [
                UIAction(label="Run again", action_type="execute",
                         payload={"tools": tools_used}),
                UIAction(label="Details", action_type="navigate",
                         payload={"view": "tool_log"}),
            ]
            components.append(UIComponent(
                component_type=ComponentType.ACTION_PANEL.value,
                data={"title": "Actions"},
                actions=actions,
                priority=1,
                ttl_seconds=30,
            ))

        return components

    def build_proactive_card(self, event_type: str, title: str,
                              body: str, actions: list[dict] = None) -> UIComponent:
        """Build a proactive suggestion/reminder card."""
        ui_actions = []
        if actions:
            for a in actions:
                ui_actions.append(UIAction(
                    label=a.get("label", "OK"),
                    action_type=a.get("type", "confirm"),
                    payload=a.get("payload", {}),
                    style=a.get("style", "default"),
                ))
        else:
            ui_actions = [
                UIAction(label="Got it", action_type="dismiss"),
                UIAction(label="Do it", action_type="confirm", style="primary"),
            ]

        return UIComponent(
            component_type=ComponentType.SUGGESTION_CARD.value,
            data={"title": title, "body": body, "event_type": event_type},
            actions=ui_actions,
            style={"variant": "proactive", "glow": True},
            priority=5,
            ttl_seconds=300,  # 5 minutes
        )
