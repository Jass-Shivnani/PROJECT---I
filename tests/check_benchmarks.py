import httpx
import json

print("Connecting to Hugging Face GAIA benchmark API...")
try:
    url = "https://datasets-server.huggingface.co/rows?dataset=gaia-benchmark%2FGAIA&config=2023_level1&split=validation&offset=0&limit=10"
    r = httpx.get(url, timeout=15)
    print("GAIA HTTP Status:", r.status_code)
    if r.status_code == 200:
        rows = r.json().get("rows", [])
        print(f"Successfully connected! Fetched {len(rows)} real GAIA benchmark rows.")
        for i, row in enumerate(rows[:5]):
            d = row.get("row", {})
            print(f"Task {i+1} [ID: {d.get('task_id')}]:")
            print(f"  Level: {d.get('Level')}")
            print(f"  Question: {d.get('Question')[:120]}...")
            print(f"  Ground Truth Answer: {d.get('Final answer')}")
            print(f"  File Attachment: {d.get('file_name')}")
            print("-" * 60)
    else:
        print("Response:", r.text[:200])
except Exception as e:
    print("Error:", e)
