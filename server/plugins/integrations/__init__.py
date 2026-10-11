"""
Dione AI -- Modular Integration Plugins Framework
================================================
Clean, plugin-based architecture for external integrations.
Each integration lives in its own dedicated module.
"""

from .base import (
    AuthType,
    IntegrationStatus,
    IntegrationConfig,
    IntegrationCredentials,
    HookEvent,
    IntegrationHookContext,
    CredentialVault,
    BaseIntegration,
)
from .registry import (
    IntegrationRegistry,
    ALL_INTEGRATIONS,
    create_default_registry,
)
from .google_drive import GoogleDriveIntegration
from .google_photos import GooglePhotosIntegration
from .google_mail import GoogleMailIntegration
from .google_calendar import GoogleCalendarIntegration
from .slack import SlackIntegration
from .instagram import InstagramIntegration
from .whatsapp import WhatsAppIntegration
from .telegram import TelegramIntegration

__all__ = [
    "AuthType",
    "IntegrationStatus",
    "IntegrationConfig",
    "IntegrationCredentials",
    "HookEvent",
    "IntegrationHookContext",
    "CredentialVault",
    "BaseIntegration",
    "IntegrationRegistry",
    "ALL_INTEGRATIONS",
    "create_default_registry",
    "GoogleDriveIntegration",
    "GooglePhotosIntegration",
    "GoogleMailIntegration",
    "GoogleCalendarIntegration",
    "SlackIntegration",
    "InstagramIntegration",
    "WhatsAppIntegration",
    "TelegramIntegration",
]
