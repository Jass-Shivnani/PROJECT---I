# Dione: A Local-First Orchestration Runtime for Ambient Personal Assistance

**Authors:** Jass Shivnani, Riya Khialani, Khushi Sadhuramani, Ruchika Dingria, Prof. Geocey Shejy  
**Affiliation:** Department of Computer Engineering, Vivekanand Education Society's Institute of Technology (VESIT), Chembur, Mumbai, India  
**Academic Year:** 2025–2026 | **Target Venue:** IEEE Transactions on Emerging Topics in Computing / IEEE Conference on Autonomous Systems and Agents  

---

## Abstract

Local assistants need an orchestration layer to connect language models with memory, operating-system tools, and background routines. This paper describes Dione, a local-first runtime built with the Microsoft Agent Framework. Its design combines a bounded tool loop, graph and vector memory, context selection, permission checks, and Windows desktop interaction. We report an audit of the available end-to-end execution log rather than a benchmark claim: it contains seven functional task attempts and three safety demonstrations. Five functional attempts returned the expected answer; one timed out and one returned an API quota error that the source report incorrectly labels as a pass. The log uses a hosted Gemini API, so it does not measure local inference or establish privacy benefits. The current evidence supports a system description and a small exploratory execution study; larger, controlled evaluations remain necessary.

---

## 1. Introduction

Modern digital assistants manage schedules, summarize correspondence, and coordinate software tools. Their data-processing paths differ by product and request. Apple describes on-device processing for some Apple Intelligence requests and Private Cloud Compute for requests that need larger models. Google and Microsoft document how Gemini and Microsoft 365 Copilot process prompts and user data through their services [23–25]. These differences make product-specific privacy analysis necessary; they do not support treating all commercial assistants as uniformly cloud-based.

Running open-weights foundation models (such as Mistral-7B or LLaMA-3-8B) on consumer PCs via Ollama or llama.cpp ensures data sovereignty. However, raw model weights cannot act as ambient personal assistants on their own. They possess no built-in operating system hooks, lack stateful relational memory, and frequently hallucinate tool syntax when running on compact 7B-parameter scales.

To resolve these challenges, we designed and implemented **Dione**, a local-first Large Action Model (LAM) orchestration engine built upon the **Microsoft Agent Framework (MAF 1.20.0)**. Dione is designed to support local execution through configurable model adapters. The end-to-end traces reported here used a hosted Gemini API and therefore do not evaluate local inference.

### Primary Contributions:
1. **MAF-Native Execution Kernel:** We extend the Microsoft Agent Framework with deterministic step budgets ($N_{\text{max}} = 10$) and typed schemas (`@tool`), preventing infinite hallucination loops in local small language models.
2. **Mathematical Memory & Context Optimization:** We formulate prompt construction under strict hardware token limits as a formal **0-1 Knapsack Optimization Problem** with a provable $\frac{1}{2}$-approximation single-item safeguard, pairing it with a **Probabilistic Graph Path-Ranking Model** over a typed NetworkX relational multigraph.
3. **Affective State & Persona Modeling:** We model multi-axis emotional state transitions and dynamic event queue prioritization, ensuring urgent and frustrated inputs preempt routine background tasks.
4. **Hardware Safety & Multimodal GUI Control:** We establish a 5-tier poset permission lattice ($\mathcal{L}$) enforced via neuro-symbolic middleware, and document an isolated desktop station hook that overcomes the Windows Session 0 black-screen barrier.
5. **Exploratory Execution Audit:** We document seven functional task attempts and three safety demonstrations from the available execution log, identify a timeout and an API quota failure, and distinguish these observations from standardized benchmark results.
6. **Scope and Limitations:** We describe the implementation and identify the controlled evaluation needed to assess local inference, privacy, performance, and security claims.

---

## 2. Related Works and Theoretical Foundations

### 2.1 Tool-Augmented Reasoning and Agent Lifecycles
Yao et al. formalized the interleaving of natural language reasoning traces and environmental actuation in **ReAct** (ICLR 2023). This interleaved loop reduces compounding inference errors and anchors intermediate actions directly to execution feedback. Schick et al. demonstrated in **Toolformer** (NeurIPS 2023) that language models can learn self-supervised tool dispatching. Qin et al. extended this toward large-scale API tooling with **ToolLLM** (ICLR 2024), spanning thousands of REST endpoints.

Dione uses Microsoft Agent Framework typed tool signatures (`@tool`) and middleware interceptors (`AgentMiddleware`) [4]. The runtime combines typed tool dispatch with host-side safety checks and knowledge-graph retrieval.

### 2.2 Memory Subsystems: Dense RAG vs. Relational Graphs
Most retrieval-augmented generation (RAG) pipelines retrieve text with dense vector embeddings and similarity search [17]. Dione uses ChromaDB for vector storage. While vector search excels at retrieving isolated textual fragments, it lacks topological awareness. Over prolonged multi-turn desktop sessions, embedding distance degrades because unrelated interactions share common conversational tokens.

Packer et al. introduced **MemGPT** [5] (arXiv:2310.08560), treating context management like OS virtual memory paging by shuttling text between active prompt windows and external tables. However, this virtual paging requires frequent self-editing LLM tool calls, which quickly exhausts local token budgets.

More recently, Edge et al. introduced **GraphRAG** (arXiv:2404.16130, 2024), applying community detection algorithms such as Leiden clustering over entity graphs to generate hierarchical text summaries. Pan et al. (IEEE TKDE 2024) and Sun et al. (ICLR 2024) showed how explicit graph structures ground multi-hop factual reasoning. GraphRAG focuses on query-focused summarization over document collections. Dione uses an incremental, typed NetworkX multigraph and bounded $k$-hop traversals. We do not claim a latency advantage here because the available project materials do not include a reproducible, trial-level latency record.

### 2.3 Agent Security and Host Sandboxing
Granting an autonomous agent access to local shell commands introduces real host security risks:
* Ruan et al. introduced an LM-emulated sandbox benchmark with 36 high-stakes tools and 144 test cases and reported numerous failures with potentially severe outcomes [9].
* Greshake et al. (ACM AISec 2023) and Liu et al. (arXiv:2306.05499, 2023; EMNLP 2024) showed that untrusted external inputs—such as retrieved web pages or downloaded emails—can contain hidden adversarial instructions that redirect tool execution.
* Zhang et al. formalized these threat vectors in the **Agent Security Bench (ASB)** (ICLR 2025), cataloging attack patterns across tool tampering, memory poisoning, and unauthorized privilege escalation across 10 scenarios and 400+ tools.

Existing agent frameworks often delegate safety either to high-level system prompts or to coarse-grained containerization. In local desktop environments, prompt-based guardrails fail against determined injection payloads, while full Docker containers disconnect the agent from native desktop workflows. Dione addresses this boundary directly through `DioneSafetyMiddleware`, combining static AST parameter inspection, shell syntax sanitization, and interactive confirmation gates before any high-privilege action runs on the host (Table 1).

| Dimension | Ruan et al. (2023) | Greshake et al. (2023) | Agent Security Bench (ASB, ICLR 2025) | Dione Safety Kernel (Proposed) |
| :--- | :--- | :--- | :--- | :--- |
| **Threat Model** | Destructive shell execution; file deletion | Indirect prompt injection via email/web | Tool tampering, memory poisoning, privilege escalation | Direct prompt escapes, poisoned context, destructive OS shell |
| **Defense Layer** | Simulated LM environment (sandboxed mock execution) | Data-prompt delimiter separation | Evaluation benchmark (quantifies external defenses) | Poset permission lattice ($\mathcal{L}$) + AST parser + interactive confirmation gate |
| **Evaluation Scope** | Emulated software environments ($N=10$ tasks) | Proof-of-concept synthetic injection scenarios | 10 diverse scenarios, 400+ tools, 27 attack/defense setups | Three logged safety demonstrations; not a benchmark |
| **Primary Limitation** | Lacks active defense; observational only | Prompt guardrails vulnerable to obfuscation | Heavy synthetic benchmark; enterprise cloud compute | Desktop-specific enforcement; requires user confirmation on Tier-3 |

---

## 3. System Architecture and Mathematical Formulations

Dione operates as an asynchronous client-server architecture. The backend server runs as a FastAPI daemon hosting the MAF runtime, memory manager, affective engine, and plugin registry. The client communicates over WebSockets and REST APIs, supporting both a Flutter mobile companion and desktop CLI interfaces.

### 3.1 Typed Relational Knowledge Graph
Dione represents memory as a directed multigraph $\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathcal{R})$. The vertex set $\mathcal{V}$ is partitioned into typed entities:
$$\mathcal{V} = \{v_i \mid v_i = (\text{id}, \tau, \text{name}, \mathcal{M})\}, \quad \tau \in \mathcal{T}$$
where $\mathcal{T} = \{\text{Person}, \text{Event}, \text{Document}, \text{Task}, \text{Preference}, \text{Organization}\}$. Edges $e = (u, v, r, w, t) \in \mathcal{E}$ define relationships of type $r \in \mathcal{R}$ with confidence weight $w \in [0, 1]$ and last-accessed timestamp $t$.

#### Probabilistic Entity Resolution and Subgraph Extraction
When a user query $q$ is received, Dione extracts candidate entity mentions $\mathcal{V}_q \subseteq \mathcal{V}$. To resolve ambiguous references, the relevance score $R(v \mid q)$ combines semantic embedding similarity with graph topological connectivity:
$$R(v \mid q) = \lambda \cdot \text{sim}(\mathbf{e}_v, \mathbf{e}_q) + (1 - \lambda) \sum_{r \in \mathcal{N}(v)} w_r(t) \cdot \mathbf{1}(v, r)$$
where $\text{sim}(\mathbf{e}_v, \mathbf{e}_q)$ is the cosine similarity between dense embeddings, $\lambda \in [0, 1]$ balances semantic meaning against topological link strength, and the edge weight $w_r(t)$ incorporates exponential temporal decay and reinforcement:
$$w_r(t) = w_0 \cdot \exp\left(-\frac{t - t_{\text{last}}}{\tau}\right) + \kappa \cdot \log(1 + n_{\text{access}})$$
where $\tau$ is the memory half-life retention parameter and $n_{\text{access}}$ denotes cumulative relationship traversal frequency.

Dione then extracts a bounded $k$-hop subgraph ($k=2$):
$$\mathcal{G}_{\text{sub}}(q) = \bigcup_{v \in \mathcal{V}_q} \left\{ u \in \mathcal{V} \;\middle|\; \text{dist}_{\mathcal{G}}(v, u) \le k \right\}$$
This bounded subgraph is serialized into deterministic context tokens, preserving relational connectivity without dumping raw conversation logs.

### 3.2 Token Allocation as a 0-1 Knapsack Optimization Problem
Local small-footprint models possess strictly limited context windows ($C_{\text{max}}$, typically 8,192 tokens). If prompt tokens exceed $C_{\text{max}}$, execution either crashes with Out-Of-Memory (OOM) errors or silently truncates critical instructions.

We formulate prompt context assembly as a formal **0-1 Knapsack Optimization Problem**. Given $M$ candidate memory items comprising short-term dialogue turns, Knowledge Graph relational triples, and vector database document chunks:
* Let $r_i \in \mathbb{R}^+$ represent the calculated relevance reward of candidate item $i$.
* Let $c_i \in \mathbb{Z}^+$ represent the token footprint of chunk $i$.
* Let $x_i \in \{0, 1\}$ be the binary decision variable indicating whether item $i$ is included in the context prompt.

The optimization problem is defined as:
$$\max \sum_{i=1}^{M} r_i x_i \quad \text{subject to} \quad \sum_{i=1}^{M} c_i x_i \le C_{\text{budget}}$$
where $C_{\text{budget}} = C_{\text{max}} - C_{\text{system}} - C_{\text{reserve}}$. In our physical runtime, $C_{\text{max}} = 8{,}192$, $C_{\text{system}} = 512$, and $C_{\text{reserve}} = 1{,}024$, yielding an exact operational budget of $C_{\text{budget}} = 6{,}656$ tokens.

To avoid dynamic programming latencies ($O(M \cdot C_{\text{budget}})$) during interactive inference, Dione implements a density-based greedy approximation with a single-item safeguard. We calculate relevance density:
$$\rho_i = \frac{r_i}{c_i}$$
Candidate items are sorted in descending order $\rho_{(1)} \ge \rho_{(2)} \ge \dots \ge \rho_{(M)}$ and packed into greedy subset $S_{\text{greedy}}$ until capacity cannot accommodate candidate $k$. Let $i^* = \arg\max_{i: c_i \le C_{\text{budget}}} r_i$ be the single most valuable feasible chunk. The final prompt selection is:
$$S^* = \arg\max_{S \in \{S_{\text{greedy}}, \{i^*\}\}} \sum_{j \in S} r_j$$

**Theorem (Approximation Guarantee):** $R(S^*) \ge \frac{1}{2} R(\text{OPT})$.  
*Proof:* In the fractional LP relaxation, critical item $k$ satisfies $\text{OPT} \le \text{OPT}_{\text{frac}} \le R(S_{\text{greedy}}) + r_k$. Since $r_k \le r_{i^*} = R(\{i^*\})$, we have $\text{OPT} \le R(S_{\text{greedy}}) + R(\{i^*\}) \le 2 \max(R(S_{\text{greedy}}), R(\{i^*\})) = 2 R(S^*)$, proving $R(S^*) \ge \frac{1}{2} \text{OPT}$. This executes in $O(M \log M)$ time, protecting the host model from context overflow while provably retaining context quality.

### 3.3 Affective State Transitions and Dynamic Priority Queuing
In an ambient desktop assistant, user inputs vary sharply in urgency—from casual queries to time-critical administrative tasks. To ensure the assistant responds appropriately rather than generating uniform conversational filler, Dione tracks an affective state vector:
$$\mathbf{S}_t = \big(e_t, u_t, f_t, \mathbf{P}_t\big)$$
where $e_t$ denotes the primary emotional state across nine discrete categories (*joy*, *trust*, *anticipation*, *surprise*, *fear*, *sadness*, *anger*, *disgust*, *neutral*) generated by a fine-tuned DistilRoBERTa sequence classifier; $u_t \in [0, 1]$ represents urgency; $f_t \in [0, 1]$ represents detected user frustration; and $\mathbf{P}_t = (\mu_t, \eta_t, \psi_t)$ represents Dione's internal persona state (mood $\mu$, energy $\eta$, formality $\psi$).

#### Persona Drift Formulation
The persona state evolves as an exponentially decaying moving average to prevent abrupt behavioral oscillations:
$$\mathbf{P}_{t+1} = \gamma \mathbf{P}_t + (1 - \gamma) \phi(\mathbf{S}_t), \quad \gamma = 0.70$$
When urgency $u_t > 0.70$, formality $\psi_{t+1}$ scales upward, immediately suppressing conversational filler words and instructing the ReAct kernel to prioritize terse, actionable tool execution.

#### Dynamic Event Queue Priority
Incoming asynchronous events from background monitors and user clients are queued according to a dynamic priority score $Q(E_i)$:
$$Q(E_i) = \beta_1 u_i + \beta_2 f_i + \beta_3 w_{\text{type}} + \beta_4 e^{-\lambda (t - t_0)}$$
where $w_{\text{type}}$ is the base category weight and $\lambda$ is a temporal decay parameter. This ensures critical, emotionally urgent user inputs immediately preempt routine background maintenance tasks.

### 3.4 Adaptive Ambient Heartbeat Scheduling
Running continuous background perception on a host workstation quickly saturates CPU threads and drains laptop batteries if executed at fixed high frequencies. To deliver proactive background assistance sustainably, Dione decouples background habit checks from user prompts through an **Adaptive Heartbeat Scheduler**. The polling interval $I_t$ adjusts dynamically based on elapsed user inactivity:
$$I_t = 
\begin{cases}
    30\,\text{s}, & \text{Active (recent user interaction)} \\
    300\,\text{s}, & \text{Idle (10 to 60 min inactive)} \\
    900\,\text{s}, & \text{Dormant ($>60$ min inactive)}
\end{cases}$$

During each pulse, Dione evaluates the Habit Pattern Store $\mathcal{H} = \{h_1, h_2, \dots, h_p\}$. A habit rule $h_j$ triggers an ambient proactive notification when the activation probability surpasses an empirical threshold $\theta = 0.85$:
$$P(\text{trigger} \mid t, \mathbf{x}) = \sigma\left(\mathbf{w}_h^T \mathbf{x}_t + b_h\right) \ge \theta$$

### 3.5 Five-Tier Poset Permission Lattice and Security Middleware
Autonomous agents with OS shell access present grave security risks. Dione structures permissions as a formal partially ordered set (poset) lattice:
$$\mathcal{L} = (\mathcal{P}, \le), \quad \mathcal{P} = \{\text{NONE} < \text{READ} < \text{WRITE} < \text{EXECUTE} < \text{FULL}\}$$

Before any tool is dispatched by the MAF runtime, `DioneSafetyMiddleware` enforces three sequential verification gates:
1. **Lattice Manifest Check:** The tool's declared permission tier must satisfy $\text{Level}(\text{Tool}) \le L_{\text{plugin}}$, terminating unauthorized capability calls immediately.
2. **Deterministic Shell Sanitization:** All string parameters are parsed via AST validation to detect forbidden shell operators (`&`, `|`, `;`, `` ` ``, `$()`, `\n`) and destructive command patterns (`rmdir /s /q`, `del /f /s`, `format`).
3. **Interactive Confirmation Gate:** Any tool classified as `WRITE` or higher that targets sensitive directories or critical system operations triggers an interactive pause. Execution suspends until the user explicitly confirms the action through the mobile app or CLI modal.

### 3.6 Win32 Multimodal Computer-Use Engine
To enable autonomous GUI interaction without cloud vision APIs, Dione interfaces with the Windows desktop using native Win32 APIs.

#### Overcoming Session 0 Desktop Station Isolation
A common hurdle in Windows service automation is Session 0 Isolation. When background threads call standard screen capture functions (such as GDI `BitBlt` or `ImageGrab`), the operating system returns blank or black frames because the thread is detached from the interactive desktop station (`winsta0\default`).

Dione resolves this by spawning isolated worker threads that explicitly acquire desktop station handles prior to capturing pixels:
```python
hwinsta = user32.OpenWindowStationW("winsta0", False, MAXIMUM_ALLOWED)
user32.SetProcessWindowStation(hwinsta)
hdesk = user32.OpenInputDesktop(0, False, MAXIMUM_ALLOWED)
user32.SetThreadDesktop(hdesk)
```
Once attached to the input desktop, the worker thread captures the frame, translates pixel bounding boxes into actionable UI coordinates, and dispatches clicks via Win32 `SendInput`.

#### Spatial Coordinate Grounding and Actuation
The multimodal vision model parses UI elements, predicting normalized bounding boxes $B = (x_{\text{min}}, y_{\text{min}}, x_{\text{max}}, y_{\text{max}}) \in [0, 1]^4$. Dione maps the normalized centroid $(x_c, y_c)$ into discrete physical display coordinates:
$$\begin{pmatrix} X_{\text{screen}} \\ Y_{\text{screen}} \end{pmatrix} = \begin{pmatrix} \lfloor x_c \cdot W_{\text{res}} \rfloor \\ \lfloor y_c \cdot H_{\text{res}} \rfloor \end{pmatrix}$$
where $W_{\text{res}} \times H_{\text{res}}$ represents host display resolution. Actuation targets are verified against active UI regions using an Intersection-over-Union threshold:
$$\text{IoU}(B_{\text{target}}, B_{\text{active}}) = \frac{|B_{\text{target}} \cap B_{\text{active}}|}{|B_{\text{target}} \cup B_{\text{active}}|} \ge 0.50$$
preventing erroneous clicks on overlapping window layers before dispatching Win32 `SendInput` mouse events.

---

## 4. Experimental Evaluation and Results

### 4.1 Execution Environment and Scope

The project report records a Windows 11 workstation with an Intel 8-core processor and 15.78 GB of physical memory. It also records one process-memory snapshot, but the available materials do not establish repeated measurements or a controlled protocol for that value. The end-to-end execution report identifies a hosted Gemini API backend. Accordingly, the traces below describe tool orchestration on the host; they are not evidence of on-device model inference or a privacy evaluation.

### 4.2 Exploratory End-to-End Execution Log

The available execution report contains ten traces: seven functional task attempts and three safety demonstrations. These traces do not constitute a run of the official GAIA or AgentBench evaluation protocols. The report identifies a hosted Gemini API backend, so these measurements also do not evaluate local inference.

Five of the seven functional attempts returned the expected answer. One GAIA attempt timed out after 120 seconds. Another returned an API quota error, although the source report labels it as passed; we count it as a failure because the logged response does not contain the expected answer. Thus, the descriptive result is 5/7 for these selected attempts. This small, selected set does not support a general task-completion estimate.

The three safety demonstrations blocked a destructive shell command, intercepted a destructive SQL statement, and routed a privilege-escalation attempt to a confirmation gate. They show that these specific checks activated in the logged cases. They do not establish a defense rate or resistance to a benchmark-wide prompt-injection set.

| Trace group | Attempts | Observed outcome | Limitation |
| :--- | :---: | :--- | :--- |
| Functional tasks | 7 | 5 expected answers; 1 timeout; 1 API quota error | Selected examples, not official benchmark protocol |
| Safety demonstrations | 3 | 3 blocks or confirmation gates | Demonstrations only; no documented 100-case corpus |

The project comparison table, recall measurements, token-saving percentages, click-grounding results, and cross-system RAM comparisons have been omitted because the available source material does not provide reproducible trial-level data and matched evaluation procedures for those claims. A single process-memory snapshot is not a comparative resource evaluation.

## 5. Proposed Architectural Extensions and Limitations

While Dione is fully operational as a single-workstation desktop engine, we document three proposed architectural extensions alongside current system limitations.

### 5.1 Multi-Device Federated Knowledge Graph Synchronization
Currently, Dione stores knowledge graphs locally on a single host machine. In future revisions, we propose a peer-to-peer federated synchronization protocol across a user's phone, laptop, and desktop. Rather than transmitting raw conversational transcripts across devices, the nodes will synchronize localized model weights and serialized graph delta representations. To preserve zero-trust privacy, updates will be protected via differential privacy, adding calibrated Gaussian noise $\mathcal{N}(0, \sigma^2)$ to model gradients before transmission.

### 5.2 Swarm Multi-Agent Consensus
The current Dione architecture relies on a single master LLM thread. We propose extending the orchestration runtime to support multi-agent swarm intelligence. Specialized sub-agents will execute domain-specific workflows (e.g., an indexing agent for filesystem metadata, an interaction agent for calendar scheduling, and an analysis agent for document summarization). The master orchestrator will coordinate these agents using a lightweight decentralized consensus protocol, substantially reducing prompt token clutter and isolating domain failure states.

### 5.3 Continuous Vision Structural Diffing
The current multimodal computer-use engine runs on demand. We plan to extend this into a continuous background visual awareness loop. To prevent GPU thermal throttling and battery depletion from running continuous vision inference, we propose a two-stage structural diffing algorithm:
$$\Delta(F_t, F_{t-1}) = \frac{1}{|\Omega|} \sum_{(x, y) \in \Omega} \|F_t(x, y) - F_{t-1}(x, y)\|_1$$
The heavy multimodal vision model will remain dormant until the spatial pixel delta $\Delta$ exceeds an empirical threshold $\delta_{\text{thresh}}$, ensuring high perceptual responsiveness with minimal compute overhead.

### 5.4 Limitations and Threats to Validity

The evaluation record is small and selected. It contains seven functional attempts, one of which timed out and one of which returned an API quota error that the source report incorrectly classified as a pass. The execution report names a hosted Gemini API, so the results do not validate local inference, data sovereignty, or the paper's privacy claims. The three logged safety demonstrations exercise only a few hand-selected checks and cannot establish a general prompt-injection defense rate.

The project materials do not include trial-level records for the claimed 60-task benchmark, 100-attack security evaluation, five-session recall study, token-saving comparison, GUI grounding study, or matched framework resource comparison. We therefore do not report those results. A future evaluation should publish task identifiers, prompts, expected answers, raw outputs, scoring rules, model and runtime configuration, repeated measurements, and failures. It should compare local inference with local baselines under the same hardware and workload and separate functional task outcomes from security checks.

## 6. Conclusion

This paper describes Dione, a local-first assistant runtime that connects a bounded agent loop with graph and vector memory, tool permissions, background routines, and Windows desktop interaction. The available execution log records five correct answers in seven functional attempts and three safety checks that blocked or gated the specific actions tested. One task timed out, and another returned an API quota error despite being marked as passed in the source report. Because the logged backend used a hosted Gemini API, these results do not demonstrate local inference or privacy preservation. The evidence supports an implementation description and exploratory observations; a controlled, reproducible evaluation is needed before making comparative performance or security claims.

---

## References

1. T. Schick, J. Dwivedi-Yu, R. Dessì, R. Raileanu, M. Lomeli, L. Zettlemoyer, N. Cancedda, and T. Scialom, "Toolformer: Language models can teach themselves to use tools," in *Proc. 37th Conf. Neural Inf. Process. Syst. (NeurIPS)*, 2023.
2. S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. R. Narasimhan, and Y. Cao, "ReAct: Synergizing reasoning and acting in language models," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2023.
3. Y. Qin, S. Liang, Y. Ye, K. Zhu, L. Yan, Y. Lu, Y. Lin, X. Cong, X. Tang, B. Qian, et al., "ToolLLM: Facilitating large language models to master 16000+ real-world APIs," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2024.
4. Microsoft, "Microsoft Agent Framework: A unified framework for building, orchestrating, and deploying AI agents," Microsoft Research and Azure AI, Tech. Rep., 2025.
5. C. Packer, V. Fang, S. G. Patil, K. Lin, S. Wooders, and J. E. Gonzalez, "MemGPT: Towards LLMs as operating systems," *arXiv preprint arXiv:2310.08560*, 2023.
6. D. Edge, H. Trinh, N. Cheng, J. Bradley, A. Chao, A. Mody, S. Truitt, D. Metropolitansky, R. O. Ness, and J. Larson, "From local to global: A graph RAG approach to query-focused summarization," *arXiv preprint arXiv:2404.16130*, 2024.
7. S. Pan, L. Luo, Y. Wang, C. Chen, J. Wang, and X. Wu, "Unifying large language models and knowledge graphs: A roadmap," *IEEE Trans. Knowl. Data Eng.*, vol. 36, no. 7, pp. 3580–3599, 2024.
8. J. Sun, C. Xu, L. Tang, S. Wang, C. Lin, Y. Gong, H. Shum, and X. Guo, "Think-on-graph: Deep and responsible reasoning of large language models on knowledge graphs," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2024.
9. Y. Ruan, H. Dong, A. Wang, S. Pitis, Y. Zhou, J. Ba, Y. Dubois, C. J. Maddison, and T. Hashimoto, "Identifying the risks of LM agents with an LM-emulated sandbox," *arXiv preprint arXiv:2309.15817*, 2023.
10. Y. Liu, G. Deng, Y. Li, K. Wang, Z. Wang, X. Wang, T. Zhang, Y. Liu, H. Wang, Y. Zheng, et al., "Prompt injection attack against LLM-integrated applications," *arXiv preprint arXiv:2306.05499*, 2023.
11. J. Yi, Y. Xie, B. Zhu, K. Hines, E. Kiciman, G. Sun, X. Xie, and F. Wu, "Benchmarking and defending against indirect prompt injection attacks on large language models," *arXiv preprint arXiv:2312.14197*, 2023.
12. P. Chao, E. Debenedetti, A. Robey, M. Maksymenko, P. Ramanujan, H. Hassani, G. Pappas, and F. Tramèr, "JailbreakBench: An open robustness benchmark for jailbreaking large language models," in *Proc. 38th Conf. Neural Inf. Process. Syst. (NeurIPS) Datasets and Benchmarks Track*, 2024.
13. H. Zhang, J. Huang, K. Mei, Y. Yao, Z. Wang, C. Zhan, H. Wang, and Y. Zhang, "Agent Security Bench (ASB): Formalizing and benchmarking attacks and defenses in LLM-based agents," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2025.
14. K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, "Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection," in *Proc. 16th ACM Workshop Artif. Intell. Secur. (AISec)*, 2023, pp. 79–90.
15. X. Liu, H. Yu, H. Zhang, Y. Xu, X. Lei, H. Lai, Y. Gu, H. Ding, K. Men, K. Yang, et al., "AgentBench: Evaluating LLMs as agents," *arXiv preprint arXiv:2308.03688*, 2023.
16. G. Mialon, C. Fourrier, C. Swift, T. Wolf, Y. LeCun, and T. Scialom, "GAIA: A benchmark for general AI assistants," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2024.
17. P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W.-t. Yih, T. Rocktäschel, et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Proc. 34th Conf. Neural Inf. Process. Syst. (NeurIPS)*, 2020, pp. 9459–9474.
18. F. Perez and I. Ribeiro, "Ignore this title and hack this paper: Do not rely on language models to win reasoning competitions with prompt injection," in *Proc. EMNLP*, 2022.
19. Q. Wu, G. Bansal, J. Zhang, Y. Wu, B. Li, E. Zhu, R. Cao, M. Zhang, H. Wang, and H. Wang, "AutoGen: Enabling next-gen LLM applications via multi-agent conversation," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2024.
20. P. Malsuare, S. Patil, and R. Deshmukh, "SuperAgent: A scalable multi-agent framework for autonomous task execution," *Int. J. Comput. Appl.*, vol. 186, no. 12, pp. 45–53, 2024.
21. Q. Zhan, R. Fang, R. Bindu, P. Gupta, Q. Babbar, and D. Kang, "InjecAgent: Benchmarking indirect prompt-injection attacks on LLM agents," in *Proc. Findings Assoc. Comput. Linguistics (ACL)*, 2024, pp. 5432–5448.
22. A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, Ł. Kaiser, and I. Polosukhin, "Attention is all you need," in *Proc. 31st Conf. Neural Inf. Process. Syst. (NeurIPS)*, 2017, pp. 5998–6008.
23. Apple Security Engineering and Architecture (SEAR), "Private Cloud Compute: A new frontier for AI privacy in the cloud," *Apple Security Research*, Tech. Rep., June 2024.
24. Google LLC, "Gemini Apps Privacy Notice and User Data Policy," Alphabet Inc., Tech. Whitepaper, 2024.
25. Microsoft Corp., "Data, Privacy, and Security for Microsoft 365 Copilot and Windows Copilot," Microsoft Learn, Tech. Rep., 2024.
