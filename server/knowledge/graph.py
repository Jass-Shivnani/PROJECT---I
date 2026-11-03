"""
Dione AI — Personal Knowledge Graph (NetworkX GraphRAG with Entity Disambiguation)
==================================================================================
Implements a 2-Hop Relational Knowledge Multigraph:
1. Entity Disambiguation & Identity Resolution: Distinguishes people/entities with the same name
   (e.g., Alex from Figma vs. Alex from Capstone) and instructs the agent to ask for clarification.
2. Smart Entity Merging: Merges metadata when identity is verified; separates distinct individuals.
3. 2-Hop Graph Traversal: Explores multi-step relationships (User -> Project -> Tech) for Knapsack context.
4. Conversational Extraction: Automatically captures entities and relationship edges from dialogue turns.
5. Social Intelligence integration: Mentors, collaborators, commitments, and topic affinity.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
from loguru import logger

from server.knowledge.entities import Entity, EntityType
from server.knowledge.relations import Relation, RelationType


class KnowledgeGraph:
    """
    Personal knowledge graph using NetworkX MultiDiGraph.
    Stores entities as nodes and typed relations as edges.
    """

    def __init__(self, storage_path: str = "./data/knowledge/graph.json"):
        self.storage_path = Path(storage_path)
        self.graph = nx.MultiDiGraph()
        self._social_engine = None
        self._load()

    @property
    def social_engine(self):
        if self._social_engine is None:
            from server.knowledge.social_intelligence import SocialIntelligenceEngine
            self._social_engine = SocialIntelligenceEngine(knowledge_graph=self)
        return self._social_engine

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        """Load graph from JSON on disk."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for node_data in data.get("nodes", []):
                    entity = Entity.from_dict(node_data)
                    self.graph.add_node(entity.id, **entity.to_dict())

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
                self.sync_social_dossiers()
            except Exception as e:
                logger.error(f"Failed to load knowledge graph: {e}")
                self.graph = nx.MultiDiGraph()
        else:
            logger.info("Starting with empty knowledge graph")

    def _save(self):
        """Persist graph to JSON atomically."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            nodes = [self.graph.nodes[n] for n in self.graph.nodes]
            edges = []
            for u, v, key, data in self.graph.edges(keys=True, data=True):
                edges.append(data)

            temp_path = self.storage_path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps({"nodes": nodes, "edges": edges}, indent=2, default=str),
                encoding="utf-8"
            )
            temp_path.replace(self.storage_path)
        except Exception as e:
            logger.error(f"Failed to persist knowledge graph: {e}")

    # ------------------------------------------------------------------
    # Identity Resolution & Disambiguation
    # ------------------------------------------------------------------

    def disambiguate_entity(
        self,
        name: str,
        entity_type: Optional[EntityType] = None,
    ) -> List[dict]:
        """
        Finds all entities sharing the same name to detect ambiguity.
        Returns detailed profile cards with distinguishing traits.
        """
        clean_name = name.strip().lower()
        candidates: List[dict] = []

        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            node_name = node.get("name", "").strip().lower()
            if entity_type and node.get("type") != entity_type.value:
                continue

            # Check exact match or primary alias
            if node_name == clean_name or clean_name in node_name:
                meta = node.get("metadata", {})
                distinguisher = (
                    meta.get("distinguisher")
                    or meta.get("role")
                    or meta.get("company")
                    or meta.get("department")
                    or meta.get("email")
                    or meta.get("project")
                    or f"Created {node.get('created_at', '')[:10]}"
                )
                candidates.append({
                    "id": node_id,
                    "name": node.get("name", name),
                    "type": node.get("type", "person"),
                    "distinguisher": distinguisher,
                    "metadata": meta,
                })

        return candidates

    def add_or_merge_entity(
        self,
        entity: Entity,
        distinguisher: Optional[str] = None,
        force_new: bool = False,
    ) -> str:
        """
        Smart Identity Resolution:
        1. If email matches an existing node -> 100% same person -> Merge.
        2. If name matches AND distinguisher matches -> Merge.
        3. If name matches BUT distinguisher/role conflicts -> Create distinct separate node!
        """
        clean_name = entity.name.strip()
        etype = entity.type
        new_meta = dict(entity.metadata)
        if distinguisher:
            new_meta["distinguisher"] = distinguisher

        new_email = new_meta.get("email", "").lower().strip()
        new_dist = new_meta.get("distinguisher", "").lower().strip()

        if not force_new:
            for node_id in self.graph.nodes:
                node = self.graph.nodes[node_id]
                if node.get("type") != etype.value:
                    continue

                exist_name = node.get("name", "").strip().lower()
                exist_meta = node.get("metadata", {})
                exist_email = exist_meta.get("email", "").lower().strip()
                exist_dist = exist_meta.get("distinguisher", "").lower().strip()

                # Strong match: Identical email
                if new_email and exist_email and new_email == exist_email:
                    exist_meta.update(new_meta)
                    exist_meta["mention_count"] = exist_meta.get("mention_count", 1) + 1
                    exist_meta["last_mentioned"] = datetime.now().isoformat()
                    node["metadata"] = exist_meta
                    node["updated_at"] = datetime.now().isoformat()
                    self._save()
                    logger.debug(f"[GraphMerge] Merged via email match: {clean_name} ({node_id})")
                    return node_id

                # Match by name: Check if distinguisher is identical or unspecified
                if exist_name == clean_name.lower():
                    # If both have explicit different distinguishers, they are DIFFERENT people!
                    if new_dist and exist_dist and new_dist != exist_dist:
                        logger.info(f"[GraphDisambiguation] Detected 2 distinct entities with name '{clean_name}': '{exist_dist}' vs '{new_dist}'")
                        continue

                    # Otherwise merge into this entity
                    exist_meta.update(new_meta)
                    exist_meta["mention_count"] = exist_meta.get("mention_count", 1) + 1
                    exist_meta["last_mentioned"] = datetime.now().isoformat()
                    node["metadata"] = exist_meta
                    node["updated_at"] = datetime.now().isoformat()
                    self._save()
                    logger.debug(f"[GraphMerge] Merged matching entity: {clean_name} ({node_id})")
                    return node_id

        # Brand new entity
        if not entity.id:
            entity.id = f"ent_{uuid.uuid4().hex[:8]}"

        new_meta["mention_count"] = new_meta.get("mention_count", 1)
        entity.metadata = new_meta
        self.graph.add_node(entity.id, **entity.to_dict())
        self._save()
        logger.debug(f"[GraphAdd] Registered distinct entity: {etype.value} '{clean_name}' (ID: {entity.id}, Distinguisher: {new_dist or 'None'})")
        return entity.id

    def add_entity(self, entity: Entity) -> str:
        return self.add_or_merge_entity(entity)

    def get_entity(self, entity_id: str) -> Optional[dict]:
        return self.graph.nodes.get(entity_id)

    def find_entities(
        self,
        name: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
    ) -> List[dict]:
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
        if entity_id in self.graph.nodes:
            self.graph.remove_node(entity_id)
            self._save()
            logger.debug(f"Removed entity: {entity_id}")

    # ------------------------------------------------------------------
    # Relation Operations
    # ------------------------------------------------------------------

    def add_relation(self, relation: Relation) -> str:
        """Add a typed relation edge between two entities."""
        if not relation.id:
            relation.id = f"rel_{uuid.uuid4().hex[:8]}"

        if relation.source_id not in self.graph.nodes:
            logger.warning(f"Source entity {relation.source_id} not found in graph")
            return ""
        if relation.target_id not in self.graph.nodes:
            logger.warning(f"Target entity {relation.target_id} not found in graph")
            return ""

        for u, v, key, data in self.graph.edges(relation.source_id, keys=True, data=True):
            if v == relation.target_id and data.get("relation_type") == relation.relation_type.value:
                data["updated_at"] = datetime.now().isoformat()
                self._save()
                return key

        self.graph.add_edge(
            relation.source_id,
            relation.target_id,
            key=relation.id,
            **relation.to_dict(),
        )
        self._save()
        logger.debug(f"Added relation: {relation.source_id} --[{relation.relation_type.value}]-> {relation.target_id}")
        return relation.id

    def get_relations(self, entity_id: str) -> List[dict]:
        relations = []
        if entity_id in self.graph.nodes:
            for _, target, key, data in self.graph.edges(entity_id, keys=True, data=True):
                relations.append({
                    "direction": "outgoing",
                    "target_id": target,
                    "target": self.graph.nodes.get(target, {}),
                    **data,
                })
            for source, _, key, data in self.graph.in_edges(entity_id, keys=True, data=True):
                relations.append({
                    "direction": "incoming",
                    "source_id": source,
                    "source": self.graph.nodes.get(source, {}),
                    **data,
                })
        return relations


    def sync_social_dossiers(self):
        """Synchronize all dossiers from data/social/dossiers.json into NetworkX."""
        dossiers_path = Path("data/social/dossiers.json")
        if not dossiers_path.exists():
            return

        try:
            dossiers = json.loads(dossiers_path.read_text(encoding="utf-8"))
        except Exception as err:
            logger.warning(f"Could not load dossiers for graph sync: {err}")
            return

        user_id = "person_jass"
        # Ensure user node exists
        if user_id in dossiers:
            u_data = dossiers[user_id]
            u_ent = Entity(
                id=user_id,
                type=EntityType.PERSON,
                name=u_data.get("canonical_name", "Jass Shivnani"),
                metadata={
                    "email": u_data.get("email", "jass.shivnani@ves.ac.in"),
                    "phone": u_data.get("phone", ""),
                    "role": u_data.get("role", "Lead Systems Architect"),
                    "organization": u_data.get("organization", "VESIT Computer Engineering"),
                    "aliases": u_data.get("aliases", ["Jass", "Lead", "Architect"]),
                    "category": "lead_developer",
                    "distinguisher": u_data.get("email", "jass.shivnani@ves.ac.in"),
                }
            )
            self.graph.add_node(user_id, **u_ent.to_dict())

        changed = False
        for pid, data in dossiers.items():
            name = data.get("canonical_name", pid)
            email = data.get("email", "")
            phone = data.get("phone", "")
            role = data.get("role", "")
            org = data.get("organization", "")
            aliases = data.get("aliases", [])
            cat = data.get("category", "contact")

            ent = Entity(
                id=pid,
                type=EntityType.PERSON,
                name=name,
                metadata={
                    "email": email,
                    "phone": phone,
                    "role": role,
                    "organization": org,
                    "aliases": aliases,
                    "category": cat,
                    "distinguisher": email or role,
                    "source": "social_dossiers",
                }
            )
            self.graph.add_node(pid, **ent.to_dict())
            changed = True

            # Edges between Jass and the contact
            if pid != user_id and user_id in self.graph.nodes:
                if cat in ("mentor_professor", "head_of_dept"):
                    rel_type = RelationType.REPORTS_TO
                elif cat in ("peer_teammate", "lead_developer"):
                    rel_type = RelationType.WORKS_WITH
                else:
                    rel_type = RelationType.KNOWS

                edge_exists = False
                for u, v, k, d in self.graph.edges(user_id, keys=True, data=True):
                    if v == pid and d.get("relation_type") == rel_type.value:
                        edge_exists = True
                        break

                if not edge_exists:
                    rel = Relation(
                        id=f"rel_{user_id}_{pid}",
                        source_id=user_id,
                        target_id=pid,
                        relation_type=rel_type,
                        metadata={"context": f"{role} at {org}"}
                    )
                    self.graph.add_edge(user_id, pid, key=rel.id, **rel.to_dict())
                    changed = True

        if changed:
            self._save()
            logger.info(f"[KnowledgeGraph] Synchronized {len(dossiers)} social dossiers into NetworkX multigraph.")

    # ------------------------------------------------------------------
    # 2-Hop GraphRAG Traversal with Disambiguation Alerts
    # ------------------------------------------------------------------

    async def query_relevant(self, user_message: str, max_results: int = 5) -> str:
        """
        Traverses a 2-Hop subgraph from entities in user message.
        If multiple individuals share the same name, adds an explicit
        Assistant Disambiguation Directive for the model.
        """
        if self.graph.number_of_nodes() == 0:
            return ""

        keywords = self._extract_keywords(user_message)
        if not keywords:
            return ""

        # Step 1: Detect Potential Ambiguities
        ambiguity_notices: List[str] = []
        for kw in keywords:
            matches = self.disambiguate_entity(kw, entity_type=EntityType.PERSON)
            if len(matches) > 1:
                options_str = "; ".join(f"{c['name']} ({c['distinguisher']})" for c in matches)
                ambiguity_notices.append(
                    f"[!] [AMBIGUITY NOTICE]: The user mentioned '{kw}', but there are {len(matches)} distinct contacts with that name: {options_str}. "
                    f"If the user's intended recipient/subject is not specified, politely ask the user to clarify which {kw} they mean before proceeding."
                )

        # Step 2: Find Seed Entities
        seed_entities: List[Tuple[dict, float]] = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            node_name = node.get("name", "").lower()
            meta_str = json.dumps(node.get("metadata", {})).lower()
            combined_text = f"{node_name} {meta_str}"

            score = 0.0
            aliases = node.get("metadata", {}).get("aliases", [])
            alias_str = " ".join(aliases).lower() if isinstance(aliases, list) else ""
            for kw in keywords:
                if kw in node_name:
                    score += 3.0
                elif kw in alias_str:
                    score += 2.5
                elif kw in combined_text:
                    score += 1.0

            if score > 0:
                seed_entities.append((node, score))

        if not seed_entities and not ambiguity_notices:
            return ""

        seed_entities.sort(key=lambda x: x[1], reverse=True)
        top_seeds = seed_entities[:max_results]

        context_lines: List[str] = []
        if ambiguity_notices:
            context_lines.extend(ambiguity_notices)

        visited_nodes: Set[str] = set()

        # Step 3: Traverse 2-Hop Subgraph
        for seed_node, seed_score in top_seeds:
            s_id = seed_node.get("id", "")
            s_name = seed_node.get("name", "Unknown")
            s_type = seed_node.get("type", "entity")
            s_dist = seed_node.get("metadata", {}).get("distinguisher", "")
            dist_tag = f" ({s_dist})" if s_dist else ""
            visited_nodes.add(s_id)

            hop1_rels = self.get_relations(s_id)
            meta = seed_node.get("metadata", {})
            if s_type == "person":
                email = meta.get("email", "")
                phone = meta.get("phone", "")
                role = meta.get("role", "")
                org = meta.get("organization", "")
                aliases = meta.get("aliases", [])
                alias_part = f", Aliases: {', '.join(aliases)}" if aliases else ""
                phone_part = f", Phone: {phone}" if phone else ""
                org_part = f" at {org}" if org else ""
                person_header = f"- [PERSON / CONTACT] {s_name} <{email}> | Role: {role}{org_part}{phone_part}{alias_part}"
                context_lines.append(person_header)
            else:
                context_lines.append(f"- [{s_type.upper()}] {s_name}{dist_tag}")

            if not hop1_rels:
                continue

            for r1 in hop1_rels[:4]:
                r1_type = r1.get("relation_type", "related_to")
                if r1["direction"] == "outgoing":
                    h1_node = r1.get("target", {})
                    h1_id = r1.get("target_id")
                    arrow = "->"
                else:
                    h1_node = r1.get("source", {})
                    h1_id = r1.get("source_id")
                    arrow = "<-"

                h1_name = h1_node.get("name", "?")
                h1_type = h1_node.get("type", "entity")
                h1_dist = h1_node.get("metadata", {}).get("distinguisher", "")
                h1_tag = f" ({h1_dist})" if h1_dist else ""

                # Hop 2 Traversal from h1_id
                hop2_notes = []
                if h1_id and h1_id not in visited_nodes:
                    visited_nodes.add(h1_id)
                    h2_rels = self.get_relations(h1_id)
                    for r2 in h2_rels[:2]:
                        r2_id = r2.get("target_id") if r2["direction"] == "outgoing" else r2.get("source_id")
                        if r2_id and r2_id != s_id:
                            r2_node = r2.get("target") if r2["direction"] == "outgoing" else r2.get("source", {})
                            r2_name = r2_node.get("name", "?")
                            r2_rel = r2.get("relation_type", "related_to")
                            hop2_notes.append(f"({arrow} {r2_rel} {r2_name})")

                h2_suffix = f" {' '.join(hop2_notes)}" if hop2_notes else ""
                context_lines.append(f"- [{s_type.upper()}] {s_name}{dist_tag} {arrow} {r1_type} [{h1_type}] {h1_name}{h1_tag}{h2_suffix}")

        return "\n".join(context_lines)

    # ------------------------------------------------------------------
    # Conversational Extraction & Distinguishing Detail Mining
    # ------------------------------------------------------------------

    async def extract_and_store(self, user_message: str, assistant_response: str):
        """
        Extracts entities, roles, and relational edges from dialogue turns.
        """
        combined = f"{user_message} {assistant_response}"
        extracted_persons: List[str] = []
        extracted_projects: List[str] = []

        # 1. Extract Person Names with optional role/distinguisher
        # Pattern: "Alex from Figma", "Sarah (our designer)", "Alex my teammate"
        dist_patterns = [
            r"([A-Z][a-z]+)\s+(?:from|at)\s+([A-Za-z0-9_-]+)",
            r"([A-Z][a-z]+)\s*\(([^)]+)\)",
            r"my\s+(?:friend|colleague|mentor|manager|boss)\s+([A-Z][a-z]+)",
        ]

        found_with_dist = False
        for m in re.finditer(dist_patterns[0], combined):
            name, dist = m.group(1).strip(), m.group(2).strip()
            p_id = self.add_or_merge_entity(
                Entity(id="", name=name, type=EntityType.PERSON),
                distinguisher=f"from {dist}"
            )
            extracted_persons.append(p_id)
            found_with_dist = True

        for m in re.finditer(dist_patterns[1], combined):
            name, dist = m.group(1).strip(), m.group(2).strip()
            p_id = self.add_or_merge_entity(
                Entity(id="", name=name, type=EntityType.PERSON),
                distinguisher=dist
            )
            extracted_persons.append(p_id)
            found_with_dist = True

        # Standard person names fallback
        if not found_with_dist:
            name_patterns = [
                r"(?:tell|email|message|call|ask|meet(?:ing)?\s+with|send\s+to|from|contact|ping)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
            ]
            for pat in name_patterns:
                for m in re.finditer(pat, combined):
                    name = m.group(1).strip()
                    if len(name) > 1 and name.lower() not in {"the", "this", "that", "about", "hello", "dione"}:
                        p_id = self.add_or_merge_entity(
                            Entity(id="", name=name, type=EntityType.PERSON)
                        )
                        extracted_persons.append(p_id)

        # 2. Extract Projects / Topics
        topic_patterns = [
            r"(?:project|app|codebase|repo|system|capstone)\s+(?:called|named)?\s*[\"']?([A-Za-z][\w-]+)[\"']?",
            r"working\s+on\s+([A-Za-z][\w-]+)",
        ]
        for pat in topic_patterns:
            for m in re.finditer(pat, combined, re.IGNORECASE):
                proj_name = m.group(1).strip()
                if len(proj_name) > 2 and proj_name.lower() not in {"this", "that", "some", "your"}:
                    proj_id = self.add_or_merge_entity(
                        Entity(id="", name=proj_name, type=EntityType.PROJECT)
                    )
                    extracted_projects.append(proj_id)

        # 3. Create Relational Edges Between Discovered Entities
        for p_id in extracted_persons:
            for pr_id in extracted_projects:
                self.add_relation(
                    Relation(
                        id="",
                        source_id=p_id,
                        target_id=pr_id,
                        relation_type=RelationType.CREATED,
                        metadata={"source": "conversation_context"},
                    )
                )

    def get_most_connected(self, n: int = 10) -> List[dict]:
        if self.graph.number_of_nodes() == 0:
            return []
        centrality = nx.degree_centrality(self.graph)
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        results = []
        for node_id, score in sorted_nodes[:n]:
            node = self.graph.nodes[node_id]
            results.append({**node, "centrality": round(score, 3)})
        return results

    def find_path(self, source_id: str, target_id: str) -> List[str]:
        try:
            path = nx.shortest_path(self.graph, source_id, target_id)
            return [self.graph.nodes[n].get("name", n) for n in path]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_stats(self) -> dict:
        return {
            "total_entities": self.graph.number_of_nodes(),
            "total_relations": self.graph.number_of_edges(),
            "entities": self.graph.number_of_nodes(),
            "relationships": self.graph.number_of_edges(),
            "most_connected": self.get_most_connected(3),
        }

    def _extract_keywords(self, text: str) -> List[str]:
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "can", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "about", "what", "which", "who", "whom", "this", "that",
            "these", "those", "how", "why", "where", "when", "send", "get", "find",
            "hello", "hi", "dione", "please", "want", "like", "you", "your", "my", "me"
        }
        words = text.lower().split()
        return [w.strip(".,!?;:'\"()") for w in words if w.strip(".,!?;:'\"()") not in stopwords and len(w) > 2]

    def save(self):
        """Public alias to persist graph to disk."""
        self._save()

    def get_statistics(self) -> dict:
        """Public alias for get_stats()."""
        return self.get_stats()

    def get_entities_by_type(self, entity_type: str) -> List[dict]:
        """Return all entities matching the given type string."""
        target = entity_type.strip().lower()
        results = []
        for node_id, data in self.graph.nodes(data=True):
            t_val = str(data.get("type", "")).lower()
            if target in t_val:
                results.append({"id": node_id, **data})
        return results

    def get_connections(self, entity_id: str) -> List[dict]:
        """Return incoming and outgoing relation edges for an entity."""
        return self.get_relations(entity_id)

    def search_entities(self, query: str) -> List[dict]:
        """Search entities by substring across name and metadata."""
        return self.find_entities(name=query)
