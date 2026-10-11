import httpx
import json

gaia_l1_url = "https://raw.githubusercontent.com/stanford-ppl/Agentic_Benchmarking_For_GAIA/main/GAIA_agent_design/classified_tests/metadata_level1.jsonl"
r = httpx.get(gaia_l1_url, timeout=15)
lines = [json.loads(l) for l in r.text.strip().split("\n") if l.strip()]
print(f"Total Level 1 tasks: {len(lines)}")
for i, item in enumerate(lines[:12]):
    fn = item.get("file_name", "")
    print(f"[{i+1}] ID: {item['task_id'][:8]} | File: '{fn}'")
    print(f"    Q: {item['Question'][:130]}...")
    print(f"    Ans: {item['Final answer']}")
