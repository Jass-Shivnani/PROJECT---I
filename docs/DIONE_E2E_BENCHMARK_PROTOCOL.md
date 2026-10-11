# Dione End-to-End Benchmark

## Purpose and scope

This benchmark checks whether Dione can answer a small, fixed set of synthetic
tasks through its local REST API while selecting the expected tools. It is a
project-specific functional evaluation, not a standardized agent benchmark and
not evidence of broad real-world capability. The measured run used the
configured Gemini backend (`gemini-3.5-flash-lite`), so it does not measure
fully local inference, data locality, or privacy.

The saved run is
[`dione_e2e_benchmark_20261011T142526Z.json`](figures/dione_e2e_benchmark_20261011T142526Z.json).
The harness is [`run_e2e_research_benchmark.py`](../tests/run_e2e_research_benchmark.py).
The 30 attempts were performed in one fresh run: 10 tasks, each repeated three
times, with the same task definitions and runtime limits throughout.

## Setup and scoring

The server listened on loopback only. Every task used synthetic fixtures placed
in a temporary directory; it did not read or write the user's project files.
Host-shell execution and desktop monitoring were disabled. Agent execution was
limited to three iterations, three tool calls, and 45 seconds per attempt. The
configured model was accessed through the provider API. A request limiter
allowed no more than 65 provider requests in this run and suppressed further
requests after authentication, quota, or rate-limit errors. The run used 62
provider requests; with 113 earlier unscored/pilot requests, the cumulative
count was 175 of the authorized maximum of 178.

An attempt counted as successful only when the API returned HTTP 200, the
answer matched the task's fixed expected-answer regular expression, and all
expected tool names appeared in the returned tool trace. The 10 tasks covered
arithmetic, string reversal, counting, temporary-directory listing, reading a
fixture file, a read-only SQLite lookup, extension filtering, a CSV calculation,
synthetic knowledge-graph lookup, and a task combining file and database
operations. The exact prompts, expected tools, scores, answers, latencies, and
per-attempt provider-request counts are in the JSON artifact.

## Results

| Task | Successful attempts | Result |
|---|---:|---|
| Arithmetic | 3/3 | 100% |
| String reversal | 3/3 | 100% |
| Counting | 3/3 | 100% |
| Directory listing/count | 3/3 | 100% |
| Fixture file read | 3/3 | 100% |
| SQLite lookup | 1/3 | 33.3% |
| File extension filtering | 3/3 | 100% |
| CSV calculation | 3/3 | 100% |
| Knowledge-graph lookup | 1/3 | 33.3% |
| Combined file and database task | 3/3 | 100% |
| **Overall** | **26/30** | **86.7%** |

The four failed attempts were two SQLite lookups and two graph lookups. In each
case the runtime returned `Function invocation limit reached before a final
answer could be produced.` This is a concrete limitation under the configured
three-call ceiling: those tool paths did not reliably complete within the
budget. It should be reported as such, rather than attributing the failures to
incorrect underlying database or graph data.

End-to-end latency had a median of 9.07 seconds and a nearest-rank 95th
percentile of 36.79 seconds across 30 attempts. These figures include provider
and tool-loop time. They are specific to this machine, model, service conditions,
and request pacing; they are not local-model latency measurements.

## Interpretation limits

This is a small hand-authored task set with synthetic data, fixed answer
patterns, and only three attempts per task. It has no external baseline,
independent task authorship, blinded scoring, or confidence interval. The
86.7% result is a descriptive score for this run, not a general estimate of
Dione's reliability. The task set emphasizes basic tool-mediated correctness;
it does not test long-horizon assistance, adversarial security, concurrent
users, recovery after device failure, or quality of open-ended answers.

The earlier pilot runs were excluded from every accuracy and latency statistic
because the task definition and safety configuration changed during those
pilots. Their provider calls are included only in the cumulative cap accounting.
The scored 30-attempt run itself completed without provider errors or server
errors. Results should be reproduced with the same harness before comparison
with later code or model changes.

## Separate safety note

An earlier, unscored preflight exposed a safety concern in the existing shell
wrapper: the safety kernel reported that a command required confirmation, while
the wrapper appeared to branch only on the `allowed` flag. The available logs
do not preserve the exact arguments, so they cannot establish whether a shell
command ran. The scored benchmark disabled host-shell access; therefore, it
does not validate unrestricted shell orchestration. This issue should be
reviewed and fixed before such an evaluation is attempted.
