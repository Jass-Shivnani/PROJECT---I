import json
from pathlib import Path

path = 'server/knowledge/graph.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add sync_social_dossiers method
sync_method = '''
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
'''

if "def sync_social_dossiers" not in content:
    target_anchor = "    # ------------------------------------------------------------------\n    # 2-Hop GraphRAG Traversal with Disambiguation Alerts"
    assert target_anchor in content, "Could not find target_anchor in graph.py"
    content = content.replace(target_anchor, sync_method + "\n" + target_anchor)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added sync_social_dossiers successfully!")
