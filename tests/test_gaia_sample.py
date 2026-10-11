import httpx
import json
import time

BASE_URL = "http://127.0.0.1:8900"

def test_gaia_task(task_id, question, expected):
    print(f"\n--- Testing GAIA Task {task_id} ---")
    print(f"Question: {question[:120]}...")
    print(f"Expected: {expected}")
    
    t0 = time.time()
    with httpx.Client(timeout=90) as client:
        r = client.post(f"{BASE_URL}/api/chat", json={"message": question})
        dur = time.time() - t0
        res = r.json()
        print(f"Status: {r.status_code} in {dur:.2f}s")
        print(f"Tools Used: {res.get('tools_used', [])}")
        print(f"Dione Answer: {res.get('response', '')}")
        return res

# Test Riddle (ec09fa32)
riddle_q = """Here's a fun riddle that I think you'll enjoy.
You have been selected to play the final round of the hit new game show "Pick That Ping-Pong Ball!"
There is an opaque box filled with 10 red ping-pong balls, 10 blue ping-pong balls, and 10 yellow ping-pong balls.
What is the minimum number of balls you must draw to guarantee having at least one pair of matching colors?
State only the final number."""

test_gaia_task("ec09fa32", riddle_q, "4")

# Test Reversal logic (2d83110e)
rev_q = """.rewsna eht sa "tfel" drow eht fo etisoppo eht etirw ,ecnetnes siht dnatsrednu uoy fI. Answer with just that single word."""
test_gaia_task("2d83110e", rev_q, "Right")
