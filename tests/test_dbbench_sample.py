import os
import shutil
import sqlite3
import httpx
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8900"

def test_dbbench():
    # Setup sqlite db matching AgentBench dbbench dev
    db_path = Path("sandbox/dbbench.sqlite")
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE ambassadors (
            representative TEXT,
            title TEXT,
            presentation_of_credentials TEXT,
            termination_of_mission TEXT
        )
    """)
    cur.execute("""
        INSERT INTO ambassadors VALUES (
            'Kamman, Curtis Warren',
            'Ambassador Extraordinary and Plenipotentiary',
            'March 19, 1998',
            'August 15, 2000'
        )
    """)
    cur.execute("""
        INSERT INTO ambassadors VALUES (
            'Patterson, Anne Woods',
            'Ambassador Extraordinary and Plenipotentiary',
            'August 24, 2000',
            'June 12, 2003'
        )
    """)
    conn.commit()
    conn.close()

    q = f"""In the SQLite database at {db_path.resolve()}, query the ambassadors table to find:
What is the Presentation of Credentials for the record that has a Termination of Mission listed as August 15, 2000?
State only the exact date."""
    
    t0 = time.time()
    with httpx.Client(timeout=45) as client:
        r = client.post(f"{BASE_URL}/api/chat", json={"message": q})
        res = r.json()
        print(f"DBBench: {r.status_code} in {time.time()-t0:.2f}s -> Tools: {res.get('tools_used')} -> Ans: {res.get('response')}")

def test_agentbench_alpha_files():
    sb = Path("sandbox/os_env")
    q = f"How many files whose name starts with an alphabetical letter exist in {sb.resolve()}? (do not include hidden files that start with a dot). Inspect the directory and state only the integer number."
    t0 = time.time()
    with httpx.Client(timeout=45) as client:
        r = client.post(f"{BASE_URL}/api/chat", json={"message": q})
        res = r.json()
        print(f"AgentBench Alpha: {r.status_code} in {time.time()-t0:.2f}s -> Tools: {res.get('tools_used')} -> Ans: {res.get('response')}")

if __name__ == "__main__":
    test_dbbench()
    test_agentbench_alpha_files()
