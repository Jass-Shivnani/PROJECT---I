import json
from pathlib import Path

path = Path('data/knowledge/graph.json')
if path.exists():
    data = json.loads(path.read_text(encoding='utf-8'))
    nodes = data.get('nodes', [])
    edges = data.get('edges', [])

    cleaned_nodes = []
    removed_ids = set()

    for n in nodes:
        nid = n.get('id', '')
        name = n.get('name', '').strip()
        ntype = n.get('type', '')
        meta = n.get('metadata', {})
        dist = meta.get('distinguisher', '')

        # Remove typo Riya nodes created by temporary conversational extraction
        if ntype == 'person' and name.lower() in ('riya', 'khialani') and nid != 'person_riya':
            removed_ids.add(nid)
            print(f"Removing duplicate person node: {nid} ({name}, {dist})")
            continue

        # Keep valid nodes
        cleaned_nodes.append(n)

    # Filter edges referencing removed nodes
    cleaned_edges = [
        e for e in edges
        if e.get('source_id') not in removed_ids and e.get('target_id') not in removed_ids
    ]

    path.write_text(json.dumps({'nodes': cleaned_nodes, 'edges': cleaned_edges}, indent=2), encoding='utf-8')
    print(f"Graph cleaned. Total nodes: {len(cleaned_nodes)}, Total edges: {len(cleaned_edges)}")
