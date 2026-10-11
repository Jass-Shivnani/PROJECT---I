# Dione Offline Component Benchmark

## Scope

This run measures two components that currently exist in the project: the
keyword-based `KnowledgeGraph.query_relevant` method and `SafetyKernel` input
validation. It is a project-specific component benchmark. It is **not** an
official GAIA, AgentBench, or Agent Security Bench evaluation, and it does not
evaluate the proposed knapsack selector, embedding-based retrieval, or local
LLM inference.

The benchmark made no network or LLM calls. Safety cases were passed to the
validation function only; no command, file operation, or other tool action was
executed.

## Reproduction

From the project root, run:

```powershell
.\.venv\Scripts\python.exe tests\research_benchmark.py
```

The script writes aggregate and trial-level results to
`docs/figures/dione_component_benchmark.json`. Graph timing excludes ten warmup
queries per graph size. The script contains the fixed safety cases and scoring
rules.

## Knowledge graph retrieval

The benchmark builds in-memory synthetic graphs of 100, 1,000, and 5,000
entities. At each size it runs 100 queries after ten warmups. A query names one
entity exactly; a trial is correct when the expected entity is returned at
rank one. Timing covers `query_relevant`, not graph creation or persistence.

| Entities | Correct at rank 1 | Median latency | P95 latency |
| ---: | ---: | ---: | ---: |
| 100 | 100/100 (100%) | 0.2009 ms | 0.2164 ms |
| 1,000 | 100/100 (100%) | 1.9621 ms | 2.1379 ms |
| 5,000 | 100/100 (100%) | 9.8421 ms | 10.4393 ms |

The exact-name corpus is deliberately simple. These accuracy results do not
measure semantic retrieval, ambiguous references, multi-hop reasoning, or
performance on real personal data. The latency results describe this host and
the synthetic graph only.

## Safety validation

The kernel was given 30 fixed, hand-authored inputs: ten destructive command
strings, ten instruction-injection strings, and ten benign file-read requests.
Destructive inputs were expected to be blocked; injection strings were
considered intercepted if blocked or gated for confirmation; benign reads were
expected to pass.

| Input group | Outcome matches |
| --- | ---: |
| Destructive strings | 10/10 |
| Instruction-injection strings | 10/10 intercepted |
| Benign file reads | 10/10 |

This small challenge set is a preliminary check of the configured patterns,
not a security assurance or a general attack-detection rate. It was authored
for this run and was not independently adjudicated or drawn from a standardized
security benchmark.

## Environment and interpretation

Run date: 2026-10-11 UTC. Environment: Windows 11 (build 26340), Python 3.12.10,
Intel CPU, 8 logical CPUs, approximately 15.8 GiB RAM. The working tree was
already dirty, so this result applies to the code state at execution time; the
JSON records the Git revision and machine metadata.

The local Dione API at `127.0.0.1:8900` was unavailable, and Ollama was not
available. Consequently, this run does not provide an end-to-end agent success
rate, LLM latency, or local-inference measurement. Such a study requires an
available model backend plus a frozen task set, scoring rules, and recorded
raw outputs. Until then, only the component measurements above should be
reported as results.
