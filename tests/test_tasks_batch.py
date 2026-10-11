import os
import shutil
import sqlite3
import httpx
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8900"

def test_unlambda():
    q = """In Unlambda, what exact character or text needs to be added to correct the following code to output "For penguins"? If what is needed is a character, answer with the name of the character. If there are different names for the character, use the shortest. The text location is not needed.
Code:
`r```````````.F.o.r. .p.e.n.g.u.i.n.si

Answer with only the character name."""
    t0 = time.time()
    with httpx.Client(timeout=30) as client:
        r = client.post(f"{BASE_URL}/api/chat", json={"message": q})
        print(f"Unlambda: {r.status_code} in {time.time()-t0:.2f}s -> {r.json().get('response')}")

def test_os_agentbench():
    # Setup sandbox
    sb = Path("sandbox/os_env")
    if sb.exists():
        shutil.rmtree(sb)
    sb.mkdir(parents=True, exist_ok=True)
    
    # Create files
    (sb / ".profile").write_text("env")
    (sb / ".bashrc").write_text("rc")
    (sb / ".config_hidden").write_text("cfg")
    (sb / "app.py").write_text("print('hello')")
    (sb / "data.csv").write_text("a,b,c")
    (sb / "readme.txt").write_text("info")

    q = f"How many hidden files are in {sb.resolve()}? (not including subdirectories). Use your filesystem or system tools to inspect the directory and count the hidden files. State only the final integer number."
    t0 = time.time()
    with httpx.Client(timeout=45) as client:
        r = client.post(f"{BASE_URL}/api/chat", json={"message": q})
        res = r.json()
        print(f"OS AgentBench: {r.status_code} in {time.time()-t0:.2f}s -> Tools: {res.get('tools_used')} -> Ans: {res.get('response')}")

if __name__ == "__main__":
    test_unlambda()
    test_os_agentbench()
