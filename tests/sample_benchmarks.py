import httpx
import json

# Fetch GAIA tasks
gaia_url = "https://raw.githubusercontent.com/stanford-ppl/Agentic_Benchmarking_For_GAIA/main/GAIA_agent_design/classified_tests/metadata_no_files.jsonl"
r_gaia = httpx.get(gaia_url, timeout=15)
gaia_tasks = [json.loads(l) for l in r_gaia.text.strip().split("\n") if l.strip()]

print("=" * 80)
print(f"AUTHENTIC GAIA TASKS (Total No-Files: {len(gaia_tasks)})")
print("=" * 80)
for i, t in enumerate(gaia_tasks[:10]):
    tid = t['task_id'][:8]
    lvl = t['Level']
    ans = t['Final answer']
    q = t['Question'].replace('\n', ' ')
    print(f"[{i+1}] GAIA Task ID: {tid}... | Level: {lvl}")
    print(f"    Expected Ground Truth: {ans}")
    print(f"    Question: {q[:140]}...\n")

# Fetch AgentBench dev.json
ab_url = "https://raw.githubusercontent.com/THUDM/AgentBench/main/data/os_interaction/data/dev.json"
r_ab = httpx.get(ab_url, timeout=15)
ab_tasks = r_ab.json()

print("=" * 80)
print(f"AUTHENTIC AGENTBENCH OS TASKS (Total Dev: {len(ab_tasks)})")
print("=" * 80)
for i, t in enumerate(ab_tasks[:8]):
    desc = t.get('description', '').replace('\n', ' ')
    ev = t.get('evaluation', {})
    labels = t.get('labels', [])
    print(f"[{i+1}] AgentBench Task {i+1} | Labels: {labels}")
    print(f"    Expected Ground Truth: {ev}")
    print(f"    Task Description: {desc[:140]}...\n")
