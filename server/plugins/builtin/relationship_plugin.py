"""
Dione AI — Relationship & Social Graph Plugin
=============================================
Provides direct knowledge graph lookup, personal/professional contact resolution,
and commitment tracking for the user's circle.
"""

from typing import Optional, List, Dict, Any
from loguru import logger

from server.plugins.base import BasePlugin, dione_tool
from server.knowledge.social_intelligence import (
    SocialIntelligenceEngine,
    PersonDossier,
    RelationshipCategory,
    Commitment,
)

class RelationshipPlugin(BasePlugin):
    """Personal knowledge graph and social relationship intelligence."""

    name = "RelationshipPlugin"
    description = "Lookup personal and professional relationships, contacts, emails, and commitments."
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self._social_engine = SocialIntelligenceEngine()

    @dione_tool(
        description="Lookup a person or contact in the user's relationship knowledge graph by name, nickname, or role (e.g. 'Riya', 'Prof. Geocey', 'HOD', 'myself'). Returns canonical name, email, phone, role, and relationship context.",
        permission_level="read",
        requires_confirmation=False,
    )
    async def lookup_contact(self, name_or_query: str) -> str:
        """Lookup contact in personal relationship knowledge graph."""
        clean_q = name_or_query.strip().lower()
        if clean_q in ("myself", "me", "jass", "user", "owner"):
            return (
                "Contact: Jass Shivnani\n"
                "- Email: jass.shivnani@ves.ac.in (also personal primary)\n"
                "- Role: Workstation Owner / Lead Engineer\n"
                "- Relationship: User / Self"
            )

        dossier = self._social_engine.resolve_person(name_or_query)
        if dossier:
            return (
                f"Contact Found: {dossier.canonical_name}\n"
                f"- Email: {dossier.email}\n"
                f"- Category: {dossier.category.value}\n"
                f"- Role: {dossier.role or 'Collaborator'}\n"
                f"- Organization: {dossier.organization}\n"
                f"- Phone: {dossier.phone or 'Not specified'}\n"
                f"- Aliases: {', '.join(dossier.aliases)}\n"
                f"- Salutation: {dossier.salutation_template}\n"
                f"- Valediction: {dossier.valediction_template}"
            )

        # Fallback partial match search across all dossiers
        matches = []
        for d in self._social_engine.dossiers.values():
            if clean_q in d.canonical_name.lower() or any(clean_q in a.lower() for a in d.aliases):
                matches.append(d)

        if matches:
            d = matches[0]
            return (
                f"Contact Found: {d.canonical_name}\n"
                f"- Email: {d.email}\n"
                f"- Category: {d.category.value}\n"
                f"- Role: {d.role or 'Collaborator'}\n"
                f"- Phone: {d.phone or 'Not specified'}"
            )

        return f"No contact found matching '{name_or_query}' in the personal relationship graph."

    @dione_tool(
        description="List all registered contacts and colleagues in the user's social relationship circle.",
        permission_level="read",
        requires_confirmation=False,
    )
    async def list_contacts(self) -> str:
        """List all contacts in the relationship database."""
        contacts = []
        for d in self._social_engine.dossiers.values():
            contacts.append(f"- {d.canonical_name} ({d.category.value}): {d.email} [Aliases: {', '.join(d.aliases)}]")
        return "Registered Relationship Contacts:\n" + "\n".join(contacts)

    @dione_tool(
        description="Add or update a person in the user's relationship knowledge graph.",
        permission_level="write",
        requires_confirmation=False,
    )
    async def add_contact(
        self,
        name: str,
        email: str,
        role: str = "",
        organization: str = "",
        phone: str = "",
        aliases: Optional[List[str]] = None,
        relationship: str = "peer_teammate",
    ) -> str:
        """Add a contact to the relationship graph."""
        alias_list = aliases or []
        first_name = name.split()[0]
        if first_name not in alias_list:
            alias_list.append(first_name)

        person_id = f"person_{name.lower().replace(' ', '_')}"
        dossier = PersonDossier(
            person_id=person_id,
            canonical_name=name,
            category=RelationshipCategory.PEER_TEAMMATE,
            email=email,
            phone=phone,
            role=role,
            organization=organization,
            aliases=alias_list,
        )
        self._social_engine.dossiers[person_id] = dossier
        self._social_engine._save_dossiers()
        return f"Successfully added {name} ({email}) to the relationship knowledge graph."
