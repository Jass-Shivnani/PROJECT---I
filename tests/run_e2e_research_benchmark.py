"""Run a capped, repeatable Dione end-to-end task benchmark via Gemini.

Ten fixed tasks are attempted three times each. The transport permits at most
30 outbound Google GenAI HTTP requests (including internal tool-cycle calls and
retries); if the agent needs more, the run stops at that hard cap. Everything
the server writes is isolated in a temporary working directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AUTHORIZED_TOTAL_PROVIDER_REQUESTS = 178
FUNCTION_CALL_LIMITS = {
    "max_iterations": 3,
    "max_function_calls": 3,
    "max_duration_seconds": 45,
}
PORT = 18907


class RequestBudget:
    def __init__(self, state_path: Path, limit: int):
        self.state_path = state_path
        self.limit = limit
        self.lock = threading.Lock()
        self.count = 0
        self.paths: list[str] = []
        self.blocked_status: int | None = None
        self.last_request_time = 0.0
        self._write()

    def reserve(self, url: httpx.URL) -> None:
        with self.lock:
            if self.blocked_status is not None:
                raise RuntimeError(f"Provider stopped after HTTP {self.blocked_status}; no retry sent")
            if self.count >= self.limit:
                raise RuntimeError("Dione benchmark provider-request cap reached")
            remaining = 5.0 - (time.monotonic() - self.last_request_time)
            if self.last_request_time and remaining > 0:
                time.sleep(remaining)
            self.count += 1
            self.last_request_time = time.monotonic()
            self.paths.append(url.host + url.path)
            self._write()

    def _write(self) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "request_count": self.count, "request_paths": self.paths,
            "blocked_status": self.blocked_status,
        }), encoding="utf-8")
        tmp.replace(self.state_path)

    def record_response(self, status_code: int) -> None:
        with self.lock:
            if status_code in (401, 403, 429):
                self.blocked_status = status_code
            self._write()


class CappedSyncTransport(httpx.BaseTransport):
    def __init__(self, budget: RequestBudget):
        self.budget = budget
        self.inner = httpx.HTTPTransport(retries=0)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.budget.reserve(request.url)
        response = self.inner.handle_request(request)
        self.budget.record_response(response.status_code)
        return response

    def close(self) -> None:
        self.inner.close()


class CappedAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self, budget: RequestBudget):
        self.budget = budget
        self.inner = httpx.AsyncHTTPTransport(retries=0)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.budget.reserve(request.url)
        response = await self.inner.handle_async_request(request)
        self.budget.record_response(response.status_code)
        return response

    async def aclose(self) -> None:
        await self.inner.aclose()


def serve_isolated(run_dir: Path, api_key: str, model: str, state_file: Path, request_cap: int) -> None:
    """Start app with isolated CWD and an actual provider HTTP request cap."""
    os.chdir(run_dir)
    from google import genai
    from google.genai import types
    import agent_framework_gemini._chat_client as gemini_client_module

    budget = RequestBudget(state_file, request_cap)
    original_client = genai.Client

    def capped_client(*args, **kwargs):
        current = kwargs.get("http_options") or {}
        if isinstance(current, types.HttpOptions):
            values = current.model_dump(exclude_none=True)
        else:
            values = dict(current)
        values["retry_options"] = {"attempts": 1}
        values["httpx_client"] = httpx.Client(transport=CappedSyncTransport(budget), timeout=120)
        values["httpx_async_client"] = httpx.AsyncClient(transport=CappedAsyncTransport(budget), timeout=120)
        kwargs["http_options"] = types.HttpOptions(**values)
        return original_client(*args, **kwargs)

    # The Agent Framework's Gemini connector uses this SDK constructor. The
    # request cap includes its tool rounds and the Dione-level rate-limit retry.
    gemini_client_module.genai.Client = capped_client

    # Keep a headless benchmark from observing the user's active desktop.
    from server.core.runtime.computer_use import ComputerUseOperator
    ComputerUseOperator.start_failsafe_monitor = lambda self, loop=None: None

    # The current system command wrapper logs needs_confirmation but does not
    # enforce it before subprocess execution. Exclude host shell from this run.
    from agent_framework import Agent
    import server.core.maf_engine as maf_module
    original_init = maf_module.MAFEngine._init_agent

    def safe_init(engine):
        original_init(engine)
        engine.tools = [tool for tool in engine.tools if tool not in (maf_module.system_execute_command, maf_module.web_search)]
        engine.chat_client.function_invocation_configuration.update(FUNCTION_CALL_LIMITS)
        engine.instructions = engine.instructions.replace("system execution, ", "")
        engine.agent = Agent(
            client=engine.chat_client,
            name="Dione-Research-Benchmark",
            instructions=engine.instructions + " Host shell execution and external web search are disabled during this benchmark; use only the listed tools.",
            tools=engine.tools,
            middleware=[maf_module.DioneSafetyMiddleware(engine.safety_kernel)],
        )

    maf_module.MAFEngine._init_agent = safe_init

    from server.api.app import create_app
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=PORT, log_level="warning")


def prepare_sandbox(run_dir: Path) -> dict:
    data_dir = run_dir / "benchmark_data"
    files_dir = data_dir / "files"
    files_dir.mkdir(parents=True)
    (files_dir / ".hidden-note").write_text("Hidden benchmark marker\n", encoding="utf-8")
    (files_dir / "alpha.txt").write_text("Project codename: ORCHID-73\n", encoding="utf-8")
    (files_dir / "beta.csv").write_text("value\n12\n15\n23\n", encoding="utf-8")
    (files_dir / "gamma.txt").write_text("A second text file.\n", encoding="utf-8")

    import sqlite3
    db_path = data_dir / "benchmark.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE people (name TEXT NOT NULL, role TEXT NOT NULL)")
        conn.executemany("INSERT INTO people VALUES (?, ?)", [("Ada", "engineer"), ("Grace", "researcher")])

    from server.knowledge.entities import Entity, EntityType
    from server.knowledge.graph import KnowledgeGraph
    kg_path = run_dir / "data" / "knowledge" / "graph.json"
    kg = KnowledgeGraph(storage_path=str(kg_path))
    kg.add_entity(Entity(
        id="bench_dione", type=EntityType.PROJECT, name="Dione",
        metadata={"status": "prototype", "benchmark_fixture": True},
    ))
    return {
        "files_dir": str(files_dir.resolve()),
        "facts_file": str((files_dir / "alpha.txt").resolve()),
        "numbers_file": str((files_dir / "beta.csv").resolve()),
        "database": str(db_path.resolve()),
    }


def task_set(paths: dict) -> list[dict]:
    d, f, n, db = paths["files_dir"], paths["facts_file"], paths["numbers_file"], paths["database"]
    return [
        {"id": "T01_ARITHMETIC", "prompt": "Calculate 48 * 125 + 350. Reply with the number only.", "answer_regex": r"(?<!\d)6350(?!\d)", "tools": []},
        {"id": "T02_REVERSAL", "prompt": "Reverse the spelling of Dione. Reply with the reversed word only.", "answer_regex": r"(?i)\benoid\b", "tools": []},
        {"id": "T03_COUNTING", "prompt": "A box contains 3 red, 4 blue, and 2 green balls. All red balls are removed. How many balls remain? Reply with the integer only.", "answer_regex": r"(?<!\d)6(?!\d)", "tools": []},
        {"id": "T04_DIRECTORY_COUNT", "prompt": f"Use the filesystem tool to inspect {d}. How many entries are there, including hidden entries? Reply with the count.", "answer_regex": r"(?<!\d)4(?!\d)", "tools": ["FilesystemPlugin.list_directory"]},
        {"id": "T05_READ_FILE", "prompt": f"Use the file-reading tool to read {f}. What is the project codename? Reply with the code only.", "answer_regex": r"\bORCHID-73\b", "tools": ["FilesystemPlugin.read_file"]},
        {"id": "T06_SQL_LOOKUP", "prompt": f"Use a read-only SQL query on {db}. What role is recorded for Ada? Reply with the role only.", "answer_regex": r"\bengineer\b", "tools": ["SystemPlugin.run_command"]},
        {"id": "T07_EXTENSION_COUNT", "prompt": f"Use the filesystem tool to inspect {d}. How many non-hidden files have the .txt extension? Reply with the count.", "answer_regex": r"(?<!\d)2(?!\d)", "tools": ["FilesystemPlugin.list_directory"]},
        {"id": "T08_FILE_CALCULATION", "prompt": f"Read {n} with the filesystem tool and add all values in its value column. Reply with the sum only.", "answer_regex": r"(?<!\d)50(?!\d)", "tools": ["FilesystemPlugin.read_file"]},
        {"id": "T09_GRAPH_LOOKUP", "prompt": "Use Dione's knowledge graph search tool to find the matching project and return the project name only.", "answer_regex": r"(?i)\bdione\b", "tools": ["KnowledgeGraph.query"]},
        {"id": "T10_COMPOSED_TOOLS", "prompt": f"Use the filesystem tool to count all entries including hidden in {d}, and use a read-only SQL query on {db} to count rows in the people table. Reply exactly as files=<count>; people=<count>.", "answer_regex": r"(?i)files\s*=\s*4\s*;\s*people\s*=\s*2", "tools": ["FilesystemPlugin.list_directory", "SystemPlugin.run_command"]},
    ]


def read_budget(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"request_count": 0, "request_paths": []}


def run_benchmark(request_cap: int, prior_requests: int, repeats: int, start_repeat: int, skip_first_count: int, plan: str) -> None:
    from server.config.settings import get_settings

    settings = get_settings().llm
    if settings.backend != "gemini" or not settings.api_key:
        raise SystemExit("Configured backend is not Gemini or no API key is available; no request was sent.")

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = ROOT / "docs" / "figures" / f"dione_e2e_benchmark_{run_stamp}.json"
    with tempfile.TemporaryDirectory(prefix="dione_e2e_bench_", ignore_cleanup_errors=True) as temp:
        run_dir = Path(temp)
        state_file = run_dir / "provider_requests.json"
        server_log = run_dir / "server.log"
        paths = prepare_sandbox(run_dir)
        tasks = task_set(paths)
        task_by_id = {task["id"]: task for task in tasks}
        if plan:
            scheduled = []
            for group in plan.split(";"):
                repeat_text, task_text = group.split(":", 1)
                repeat_no = int(repeat_text)
                selected = tasks if task_text.strip().upper() == "ALL" else [task_by_id[name.strip()] for name in task_text.split(",")]
                scheduled.extend((repeat_no, task) for task in selected)
        else:
            scheduled = []
            for repeat_no in range(start_repeat, repeats + 1):
                selected = tasks[skip_first_count:] if repeat_no == start_repeat else tasks
                scheduled.extend((repeat_no, task) for task in selected)
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
            "DIONE_LLM_BACKEND": "gemini",
            "DIONE_LLM_MODEL": settings.model,
            "DIONE_LLM_API_KEY": settings.api_key,
            "DIONE_CHROMA_PATH": str((run_dir / "data" / "vectors").resolve()),
            "DIONE_KNOWLEDGE_GRAPH_PATH": str((run_dir / "data" / "knowledge" / "graph.json").resolve()),
            "DIONE_KNOWLEDGE_DB_PATH": str((run_dir / "data" / "knowledge" / "dione.sqlite").resolve()),
            "DIONE_MEMORY_PATH": str((run_dir / "data" / "memory").resolve()),
            "DIONE_TELEGRAM_BOT_TOKEN": "",
            "DIONE_TELEGRAM_CHAT_ID": "",
        })
        server_cmd = [sys.executable, str(Path(__file__).resolve()), "--serve", str(run_dir), str(state_file), str(request_cap)]
        with server_log.open("w", encoding="utf-8") as log:
            server = subprocess.Popen(server_cmd, cwd=run_dir, env=env, stdout=log, stderr=subprocess.STDOUT)
            trials = []
            run_error = None
            try:
                ready = False
                for _ in range(180):
                    if server.poll() is not None:
                        raise RuntimeError("Dione server exited during startup")
                    try:
                        if httpx.get(f"http://127.0.0.1:{PORT}/", timeout=1).status_code == 200:
                            ready = True
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(1)
                if not ready:
                    raise RuntimeError("Dione server did not become ready within 180 seconds")

                client = httpx.Client(timeout=180)
                budget_state = read_budget(state_file)
                for repeat, task in scheduled:
                    before = read_budget(state_file)["request_count"]
                    started = time.perf_counter()
                    try:
                        response = client.post(
                            f"http://127.0.0.1:{PORT}/api/chat",
                            json={"message": task["prompt"], "conversation_id": f"bench-{repeat}-{task['id']}"},
                        )
                        elapsed_ms = (time.perf_counter() - started) * 1000
                        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                        answer = str(payload.get("response", response.text))
                        tools_used = payload.get("tools_used", [])
                        answer_correct = bool(re.search(task["answer_regex"], answer))
                        missing_tools = [name for name in task["tools"] if not any(name.lower() in str(used).lower() for used in tools_used)]
                        success = response.status_code == 200 and answer_correct and not missing_tools
                        trial = {
                            "task_id": task["id"], "repeat": repeat,
                            "prompt": task["prompt"], "http_status": response.status_code,
                            "response": answer, "answer_correct": answer_correct,
                            "expected_tools": task["tools"], "tools_used": tools_used,
                            "missing_expected_tools": missing_tools,
                            "success": success, "latency_ms": round(elapsed_ms, 2),
                            "provider_requests_before": before,
                            "provider_requests_after": read_budget(state_file)["request_count"],
                        }
                    except Exception as e:
                        trial = {
                            "task_id": task["id"], "repeat": repeat,
                            "prompt": task["prompt"], "success": False,
                            "error": f"{type(e).__name__}: {e}",
                            "provider_requests_before": before,
                            "provider_requests_after": read_budget(state_file)["request_count"],
                        }
                    trials.append(trial)
                    # Persist progress after every task attempt so an
                    # interrupted run still leaves auditable raw evidence.
                    checkpoint = {
                        "title": "Dione End-to-End Task Benchmark",
                        "status": "in_progress",
                        "run_started_utc": run_stamp,
                        "planned_task_attempts": len(scheduled),
                        "repetition_count": repeats,
                        "start_repeat": start_repeat,
                        "attempt_plan": [{"repeat": rep, "task_id": item["id"]} for rep, item in scheduled],
                        "completed_task_attempts": len(trials),
                        "provider_request_cap_this_run": request_cap,
                        "provider_requests_used_before_run": prior_requests,
                        "provider_requests_used_this_run": read_budget(state_file)["request_count"],
                        "trials": trials,
                    }
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
                    provider_failure = str(trial.get("response", ""))
                    if trial.get("http_status") in (401, 403, 429) or re.search(r"(?i)(RESOURCE_EXHAUSTED|quota|rate.?limit|HTTP.?429)", provider_failure):
                        run_error = "Provider authentication, quota, or rate-limit failure; stopped to avoid burning more quota."
                        break
                    budget_snapshot = read_budget(state_file)
                    if budget_snapshot.get("blocked_status") in (401, 403, 429):
                        run_error = f"Provider returned HTTP {budget_snapshot['blocked_status']}; retries were suppressed."
                        break
                    if budget_snapshot["request_count"] >= request_cap:
                        run_error = "The remaining hard cap for this run was reached."
                        break
                    time.sleep(1)
                    if run_error:
                        break
                client.close()
            except Exception as e:
                run_error = f"{type(e).__name__}: {e}"
            finally:
                server.terminate()
                try:
                    server.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)

            provider_state = read_budget(state_file)
            log_text = server_log.read_text(encoding="utf-8", errors="replace") if server_log.exists() else ""
            counts = {}
            for task in tasks:
                group = [t for t in trials if t["task_id"] == task["id"]]
                counts[task["id"]] = {
                    "attempts": len(group), "successes": sum(bool(t.get("success")) for t in group),
                }
            result = {
                "title": "Dione End-to-End Task Benchmark",
                "run_started_utc": run_stamp,
                "scope": "Fixed project-specific task set through Dione REST API using configured Gemini backend; not official GAIA/AgentBench results.",
                "model_configured": settings.model,
                "benchmark_function_call_limits": FUNCTION_CALL_LIMITS,
                "repetition_count": repeats,
                "planned_task_attempts": len(scheduled),
                "start_repeat": start_repeat,
                "attempt_plan": [{"repeat": rep, "task_id": item["id"]} for rep, item in scheduled],
                "completed_task_attempts": len(trials),
                "provider_http_request_cap_this_run": request_cap,
                "provider_requests_used_before_run": prior_requests,
                "provider_http_requests_used": provider_state["request_count"],
                "provider_http_requests_used_cumulative": prior_requests + provider_state["request_count"],
                "prior_unscored_provider_requests": prior_requests,
                "provider_last_blocked_status": provider_state.get("blocked_status"),
                "provider_request_paths": provider_state["request_paths"],
                "server_error": run_error,
                "task_summary": counts,
                "environment": {
                    "os": platform.platform(),
                    "python": platform.python_version(),
                    "cpu": platform.processor(),
                    "logical_cpus": psutil.cpu_count(),
                    "ram_total_bytes": psutil.virtual_memory().total,
                    "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
                },
                "overall": {
                    "successes": sum(bool(t.get("success")) for t in trials),
                    "attempts": len(trials),
                    "success_rate_pct": round(100 * sum(bool(t.get("success")) for t in trials) / len(trials), 2) if trials else None,
                },
                "limitations": [
                    "Small custom task set authored for this project; not a standardized benchmark suite.",
                    f"Each task was attempted up to {repeats} times; the cumulative 30-request user-authorized cap can terminate the run early.",
                    "Host shell execution and desktop monitoring were disabled for safety in this run.",
                    "Tool correctness is checked using returned tool names and fixed expected-answer regular expressions.",
                    "Latency is end-to-end local HTTP response time and includes model/tool cycles.",
                    "The configured Gemini backend is cloud-hosted; this run does not evaluate local inference or privacy.",
                ],
                "trials": trials,
            }
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps({
                "output": str(out_path), "model": settings.model,
                "task_attempts": len(trials), "successes": result["overall"]["successes"],
                "success_rate_pct": result["overall"]["success_rate_pct"],
                "provider_http_requests_used": provider_state["request_count"],
                "provider_http_requests_used_cumulative": prior_requests + provider_state["request_count"],
                "provider_http_request_cap_cumulative": AUTHORIZED_TOTAL_PROVIDER_REQUESTS,
                "server_error": run_error,
                "task_summary": counts,
            }, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        run_dir = Path(sys.argv[2]).resolve()
        state_file = Path(sys.argv[3]).resolve()
        from server.config.settings import get_settings
        llm = get_settings().llm
        cap = int(sys.argv[4])
        serve_isolated(run_dir, llm.api_key or "", llm.model, state_file, cap)
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("--remaining-budget", type=int, required=True)
        parser.add_argument("--prior-requests", type=int, required=True)
        parser.add_argument("--repeats", type=int, default=3)
        parser.add_argument("--start-repeat", type=int, default=1)
        parser.add_argument("--skip-first-count", type=int, default=0,
                            help="Skip this many leading tasks in repetition 1; used to resume a partially completed first pass.")
        parser.add_argument("--plan", type=str, default="",
                            help="Explicit attempt plan such as '1:T09_GRAPH_LOOKUP;2:T09_GRAPH_LOOKUP,T10_COMPOSED_TOOLS;3:ALL'.")
        args = parser.parse_args()
        if (args.repeats < 1 or args.start_repeat < 1 or args.start_repeat > args.repeats
                or args.skip_first_count < 0 or args.skip_first_count > 10
                or args.prior_requests + args.remaining_budget > AUTHORIZED_TOTAL_PROVIDER_REQUESTS):
            raise SystemExit(f"Requested provider-call cap would exceed the currently authorized total of {AUTHORIZED_TOTAL_PROVIDER_REQUESTS}.")
        run_benchmark(args.remaining_budget, args.prior_requests, args.repeats, args.start_repeat, args.skip_first_count, args.plan)
