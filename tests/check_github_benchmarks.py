import httpx
import json

# Check THUDM/AgentBench repository on GitHub
print("Checking THUDM/AgentBench on GitHub...")
try:
    # Check AgentBench data directory (e.g. os_interaction / data)
    url_ab = "https://raw.githubusercontent.com/THUDM/AgentBench/main/data/os_interaction/config.json"
    r = httpx.get(url_ab, timeout=15)
    print("AgentBench OS config status:", r.status_code)
    if r.status_code == 200:
        print("AgentBench OS config preview:", r.text[:200])
except Exception as e:
    print("AgentBench check error:", e)

# Check GAIA public raw files or test split
print("\nChecking GAIA repo on GitHub...")
try:
    url_gaia = "https://raw.githubusercontent.com/gaia-benchmark/gaia/main/benchmark/gaia.py"
    r = httpx.get(url_gaia, timeout=15)
    print("GAIA GitHub status:", r.status_code)
except Exception as e:
    print("GAIA check error:", e)
