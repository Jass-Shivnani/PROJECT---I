"""
Dione AI — Knowledge Graph Query Engine

Provides natural language querying over the knowledge graph.
Translates user questions into graph traversals.
"""

from typing import Optional
from loguru import logger

from server.knowledge.graph import KnowledgeGraph
from server.knowledge.entities import EntityType


class KnowledgeQueryEngine:
    """
    Translates natural language queries into knowledge graph operations.
    
    Examples:
    - "Who sent me that PDF?" → Find Document(type=pdf, recent) → traverse SENT relation → Person
    - "What's Alice working on?" → Find Person(name=Alice) → traverse PART_OF → Project
    - "When is my next meeting?" → Find Event(upcoming) → return details
    """

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    async def query(self, question: str) -> str:
        """
        Answer a question using the knowledge graph.
        
        Returns a natural language summary of the graph data.
        """
        question_lower = question.lower()

        # Detect query type and route accordingly
        if any(w in question_lower for w in ["who", "person", "people"]):
            return await self._query_people(question)
        elif any(w in question_lower for w in ["when", "meeting", "event", "calendar"]):
            return await self._query_events(question)
        elif any(w in question_lower for w in ["file", "document", "pdf", "report"]):
            return await self._query_documents(question)
        elif any(w in question_lower for w in ["task", "todo", "assigned"]):
            return await self._query_tasks(question)
        else:
            # General query — use the graph's relevance search
            return await self.graph.query_relevant(question)

    async def _query_people(self, question: str) -> str:
        """Query for people-related information."""
        people = self.graph.find_entities(entity_type=EntityType.PERSON)
        if not people:
            return "I don't have any people in my knowledge graph yet."

        # Extract name if mentioned
        for person in people:
            name = person.get("name", "").lower()
            if name and name in question.lower():
                # Found a specific person — get their connections
                relations = self.graph.get_relations(person.get("id", ""))
                context = f"About {person['name']}:\n"
                for rel in relations:
                    if rel["direction"] == "outgoing":
                        target = rel.get("target", {}).get("name", "?")
                        context += f"  • {rel.get('relation_type', '?')} → {target}\n"
                    else:
                        source = rel.get("source", {}).get("name", "?")
                        context += f"  • {source} → {rel.get('relation_type', '?')}\n"
                return context

        # No specific person — list known people
        names = [p.get("name", "?") for p in people[:10]]
        return f"Known people: {', '.join(names)}"

    async def _query_events(self, question: str) -> str:
        """Query for event-related information."""
        events = self.graph.find_entities(entity_type=EntityType.EVENT)
        if not events:
            return "No events in the knowledge graph."
        
        summaries = []
        for event in events[:5]:
            meta = event.get("metadata", {})
            summaries.append(
                f"• {event['name']} ({meta.get('start_time', 'no time')})"
            )
        return "Events:\n" + "\n".join(summaries)

    async def _query_documents(self, question: str) -> str:
        """Query for document-related information."""
        docs = self.graph.find_entities(entity_type=EntityType.DOCUMENT)
        if not docs:
            return "No documents tracked in the knowledge graph."
        
        summaries = []
        for doc in docs[:5]:
            meta = doc.get("metadata", {})
            summaries.append(
                f"• {doc['name']} (from {meta.get('source', 'unknown')}, "
                f"{meta.get('file_type', 'unknown')})"
            )
        return "Documents:\n" + "\n".join(summaries)

    async def _query_tasks(self, question: str) -> str:
        """Query for task-related information."""
        tasks = self.graph.find_entities(entity_type=EntityType.TASK)
        if not tasks:
            return "No tasks in the knowledge graph."
        
        summaries = []
        for task in tasks[:10]:
            meta = task.get("metadata", {})
            status = meta.get("status", "unknown")
            priority = meta.get("priority", "medium")
            summaries.append(f"• [{status}] {task['name']} (priority: {priority})")
        return "Tasks:\n" + "\n".join(summaries)
