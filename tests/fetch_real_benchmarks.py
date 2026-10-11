import httpx
import json

print("Fetching Agent217_test_set_submission.jsonl from Stanford repository...")
url = "https://raw.githubusercontent.com/stanford-ppl/Agentic_Benchmarking_For_GAIA/main/Agent217_test_set_submission.jsonl"
r = httpx.get(url, timeout=20)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    lines = [l for l in r.text.strip().split("\n") if l.strip()]
    print(f"Total lines in submission file: {len(lines)}")
    for i, line in enumerate(lines[:5]):
        print(f"Line {i+1}: {line[:150]}...")

# Also check contents of GAIA_agent_design
url_dir = "https://api.github.com/repos/stanford-ppl/Agentic_Benchmarking_For_GAIA/contents/GAIA_agent_design"
r_dir = httpx.get(url_dir, timeout=10)
if r_dir.status_code == 200:
    print("\nContents of GAIA_agent_design:")
    for item in r_dir.json():
        print(f"  {item.get('name')} ({item.get('type')})")
