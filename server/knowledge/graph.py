"""
Dione AI — Knowledge Graph

The core personal knowledge graph that connects the user's
digital life into a structured, queryable network.

This is Dione's STAR FACTOR #1: Instead of flat markdown files,
Dione builds a real graph of entities (people, events, documents)
connected by typed relationships. This allows deep contextual
understanding that simple keyword search or RAG alone cannot achieve.

Example: "Send that report to the person I met yesterday"
- Graph traversal: User -> attended_event(yesterday) -> participant(Person) 
                   User -> received_document(recent, type=report) -> Document
- Result: Dione knows WHO and WHAT without any ambiguity.
"""

import json
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime
import networkx as nx
from loguru import logger

from server.knowledge.entities import Entity, EntityType
from server.knowledge.relations import Relation, RelationType


class KnowledgeGraph:
    """
    Personal knowledge graph using NetworkX.
    
    Stores entities as nodes and relations as edges in a directed
    multigraph. Persisted to disk as JSON.
    
    For production, this can be swapped to Neo4j or similar.
    """

    def __init__(self, storage_path: str = "./data/knowledge/graph.json"):
        self.storage_path = Path(storage_path)
        self.graph = nx.MultiDiGraph()
        self._load()

    def _load(self):
        """Load graph from disk."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                
                # Restore nodes
                for node_data in data.get("nodes", []):
                    entity = Entity.from_dict(node_data)
                    self.graph.add_node(
                        entity.id,
                        **entity.to_dict(),
                    )

                # Restore edges
                for edge_data in data.get("edges", []):
                    relation = Relation.from_dict(edge_data)
                    self.graph.add_edge(
                        relation.source_id,
                        relation.target_id,
                        key=relation.id,
                        **relation.to_dict(),
                    )

                logger.info(
                    f"Knowledge graph loaded: {self.graph.number_of_nodes()} entities, "
                    f"{self.graph.number_of_edges()} relations"
                )
            except Exception as e:
                logger.error(f"Failed to load knowledge graph: {e}")
                self.graph = nx.MultiDiGraph()
        else:
            logger.info("Starting with empty knowledge graph")

    def _save(self):
        """Persist graph to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        nodes = [self.graph.nodes[n] for n in self.graph.nodes]
        edges = []
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            edges.append(data)

        self.storage_path.write_text(
            json.dumps({"nodes": nodes, "edges": edges}, indent=2, default=str)
        )

    # ------------------------------------------------------------------
    # Entity operations
    # ------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> str:
        """Add an entity (node) to the graph."""
        if not entity.id:
            entity.id = str(uuid.uuid4())[:8]

        self.graph.add_node(entity.id, **entity.to_dict())
        self._save()
        logger.debug(f"Added entity: {entity.type.value} '{entity.name}' ({entity.id})")
        return entity.id

    def get_entity(self, entity_id: str) -> Optional[dict]:
        """Get an entity by ID."""
        if entity_id in self.graph.nodes:
            return self.graph.nodes[entity_id]
        return None

    def find_entities(
        self,
        name: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
    ) -> list[dict]:
        """Find entities by name and/or type."""
        results = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            
            if entity_type and node.get("type") != entity_type.value:
                continue
            if name and name.lower() not in node.get("name", "").lower():
                continue
                
            results.append(node)
        
        return results

    def remove_entity(self, entity_id: str):
        """Remove an entity and all its relations."""
        if entity_id in self.graph.nodes:
            self.graph.remove_node(entity_id)
            self._save()
            logger.debug(f"Removed entity: {entity_id}")

    # ------------------------------------------------------------------
    # Relation operations
    # ------------------------------------------------------------------

    def add_relation(self, relation: Relation) -> str:
        """Add a relation (edge) between two entities."""
        if not relation.id:
            relation.id = str(uuid.uuid4())[:8]

        if relation.source_id not in self.graph.nodes:
            logger.warning(f"Source entity {relation.source_id} not found")
            return ""
        if relation.target_id not in self.graph.nodes:
            logger.warning(f"Target entity {relation.target_id} not found")
            return ""

        self.graph.add_edge(
            relation.source_id,
            relation.target_id,
            key=relation.id,
            **relation.to_dict(),
        )
        self._save()
        logger.debug(
            f"Added relation: {relation.source_id} --[{relation.relation_type.value}]-> {relation.target_id}"
        )
        return relation.id

    def get_relations(self, entity_id: str) -> list[dict]:
        """Get all relations involving an entity."""
        relations = []
        
        # Outgoing edges
        if entity_id in self.graph.nodes:
            for _, target, key, data in self.graph.edges(entity_id, keys=True, data=True):
                relations.append({
                    "direction": "outgoing",
                    "target": self.graph.nodes.get(target, {}),
                    **data,
                })
        
        # Incoming edges
        for source, target, key, data in self.graph.edges(keys=True, data=True):
            if target == entity_id:
                relations.append({
                    "direction": "incoming",
                    "source": self.graph.nodes.get(source, {}),
                    **data,
                })
        
        return relations

    # ------------------------------------------------------------------
    # Query operations (the magic)
    # ------------------------------------------------------------------

    async def query_relevant(self, user_message: str, max_results: int = 5) -> str:
        """
        Query the knowledge graph for context relevant to a user message.
        
        This is the key differentiator: given a natural language message,
        find the most relevant entities and their connections.
        
        Strategy:
        1. Extract key terms from the message
        2. Find matching entities
        3. Traverse their connections to build context
        """
        if self.graph.number_of_nodes() == 0:
            return ""

        # Simple keyword matching (TODO: replace with embedding-based search)
        keywords = self._extract_keywords(user_message)
        
        matching_entities = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            node_text = f"{node.get('name', '')} {json.dumps(node.get('metadata', {}))}".lower()
            
            relevance = sum(1 for kw in keywords if kw in node_text)
            if relevance > 0:
                matching_entities.append((node, relevance))

        # Sort by relevance
        matching_entities.sort(key=lambda x: x[1], reverse=True)
        top_entities = matching_entities[:max_results]

        if not top_entities:
            return ""

        # Build context string with entity connections
        context_parts = []
        for entity, _ in top_entities:
            entity_id = entity.get("id", "")
            name = entity.get("name", "unknown")
            etype = entity.get("type", "unknown")
            
            # Get connections
            relations = self.get_relations(entity_id)
            relation_strs = []
            for rel in relations[:3]:  # Max 3 connections per entity
                if rel["direction"] == "outgoing":
                    target_name = rel.get("target", {}).get("name", "?")
                    rel_type = rel.get("relation_type", "related_to")
                    relation_strs.append(f"  → {rel_type} → {target_name}")
                else:
                    source_name = rel.get("source", {}).get("name", "?")
                    rel_type = rel.get("relation_type", "related_to")
                    relation_strs.append(f"  ← {rel_type} ← {source_name}")

            context_parts.append(
                f"[{etype}] {name}" +
                ("\n" + "\n".join(relation_strs) if relation_strs else "")
            )

        return "\n".join(context_parts)

    async def extract_and_store(self, user_message: str, assistant_response: str):
        """
        Extract entities and relations from a conversation turn
        and add them to the knowledge graph.
        
        This is called after every interaction to continuously
        build the user's personal knowledge graph.
        
        TODO: Use the LLM to extract entities/relations via NER
        """
        # For now, this is a placeholder for LLM-based entity extraction
        # In production, the LLM would parse the conversation to identify:
        # - New people mentioned
        # - Events/meetings discussed
        # - Documents referenced
        # - Tasks assigned
        # - Relationships between them
        pass

    # ------------------------------------------------------------------
    # Graph analytics
    # ------------------------------------------------------------------

    def get_most_connected(self, n: int = 10) -> list[dict]:
        """Get the most connected entities (highest degree centrality)."""
        if self.graph.number_of_nodes() == 0:
            return []
            
        centrality = nx.degree_centrality(self.graph)
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for node_id, score in sorted_nodes[:n]:
            node = self.graph.nodes[node_id]
            results.append({**node, "centrality": round(score, 3)})
        
        return results

    def find_path(self, source_id: str, target_id: str) -> list[str]:
        """Find the shortest path between two entities."""
        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return [self.graph.nodes[n].get("name", n) for n in path]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_stats(self) -> dict:
        """Get graph statistics."""
        return {
            "total_entities": self.graph.number_of_nodes(),
            "total_relations": self.graph.number_of_edges(),
            "entity_types": self._count_by_type(),
            "most_connected": self.get_most_connected(3),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text for graph search."""
        # Simple keyword extraction (stopword removal)
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again", "further",
            "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "just", "because",
            "but", "and", "or", "if", "while", "about", "up", "my",
            "me", "i", "you", "your", "it", "its", "this", "that",
            "what", "which", "who", "whom", "these", "those", "am",
            "send", "get", "find", "show", "tell", "please", "want",
        }

        words = text.lower().split()
        return [w.strip(".,!?;:'\"") for w in words if w.lower() not in stopwords and len(w) > 2]

    def _count_by_type(self) -> dict:
        """Count entities by type."""
        counts = {}
        for node_id in self.graph.nodes:
            etype = self.graph.nodes[node_id].get("type", "unknown")
            counts[etype] = counts.get(etype, 0) + 1
        return counts
