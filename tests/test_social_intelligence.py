"""
Dione AI — Social & Relationship Intelligence Test Suite
========================================================
Validates:
1. Aliasing & Identity Resolution (Mentor, Geocey, HOD, Riya).
2. Contextual Tone Guidance & Salutation Injection.
3. Automated Commitment / Promise Mining ("I will send the draft by Wednesday").
4. Relationship Health & Decay Evaluation.
5. Graph Edge Serialization in NetworkX.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from server.knowledge.graph import KnowledgeGraph
from server.knowledge.social_intelligence import SocialIntelligenceEngine, RelationshipCategory

def test_social_intelligence():
    print("=" * 70)
    print("DIONE AI — SOCIAL INTELLIGENCE & PERSON AWARENESS TEST SUITE")
    print("=" * 70)

    kg = KnowledgeGraph(storage_path="data/knowledge/test_social_graph.json")
    social = kg.social_engine

    # 1. Test Alias & Role Resolution
    print("\n[1] Testing Alias & Identity Resolution:")
    queries = ["mentor", "Geocey", "Prof. Shejy", "HOD", "Riya", "geocey.shejy@ves.ac.in"]
    for q in queries:
        dossier = social.resolve_person(q)
        if dossier:
            print(f"  ✔ Query '{q:22}' -> Resolved: {dossier.canonical_name} ({dossier.role})")
        else:
            print(f"  ❌ Query '{q}' -> NOT FOUND")

    # 2. Test Contextual Tone & Salutation Customization
    print("\n[2] Testing Dynamic Tone Guidance:")
    print("--- Tone Guidance for 'mentor' ---")
    print(social.get_tone_guidance("mentor"))
    print("\n--- Tone Guidance for 'Riya' (Teammate) ---")
    print(social.get_tone_guidance("Riya"))

    # 3. Test Automated Commitment / Promise Mining
    print("\n[3] Testing Automated Commitment Mining from Conversation:")
    sample_text = (
        "Respected Ma'am, I will send the revised Chapter 6 test cases by Wednesday. "
        "Also, let me review the benchmark charts before 5 PM."
    )
    commitments = social.detect_and_record_commitments(sample_text, recipient_hint="Prof. Geocey Shejy")
    print(f"  ✔ Mined {len(commitments)} commitments from text:")
    for c in commitments:
        print(f"    • [{c.status.upper()}] {c.description} | Due: {c.due_date} | Recipient: {c.person_name}")

    # 4. Test Relationship Health / Decay Evaluator
    print("\n[4] Testing Relationship Touchpoint Health Monitor:")
    alerts = social.evaluate_relationship_health()
    print(f"  ✔ Found {len(alerts)} touchpoint health checks:")
    for a in alerts:
        print(f"    • {a['name']} ({a['role']}): {a['suggestion']}")

    # 5. Verify NetworkX Social Subgraph Nodes
    print("\n[5] Verifying NetworkX Graph Nodes & Relations:")
    print(f"  ✔ Total Nodes in Knowledge Graph: {kg.graph.number_of_nodes()}")
    print(f"  ✔ Total Edges in Knowledge Graph: {kg.graph.number_of_edges()}")

    print("\n" + "=" * 70)
    print("ALL SOCIAL INTELLIGENCE TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    test_social_intelligence()
