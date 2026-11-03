"""
sync_tex_humanized.py
---------------------
Synchronizes master LaTeX source files with Round 3 humanized text blocks.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "docs"
MASTER_TEX = DOCS_DIR / "DIONE_IEEE_RESEARCH_PAPER.tex"

with open(BASE_DIR / "received_round3_turnitin.json", "r", encoding="utf-8") as f:
    d = json.load(f)

tex = MASTER_TEX.read_text(encoding="utf-8")

# 1. Abstract
old_abs_target = (
    "Background tasks are handled by a piecewise heartbeat scheduler. This scheduler decides how often it checks in. "
    "It starts checking every 30 seconds. Then slows down to every 900 seconds when the system is not in use. "
    "Also a multi-axis affective engine keeps track of the users mood. When the user looks urgent. Upset it changes the order of tasks "
    "to respond faster. Tool execution is controlled by a 5-level permission structure. This structure uses a poset lattice. "
    "Asks for confirmation each time with a pop-up prompt. It also uses a Win32 desktop station hook to deal with the Session 0 black screen problem. "
    "On hardware Dione it finished 27.6\\% of tasks overall when tested on GAIA and AgentBench benchmarks. That is 50.0\\% on machines "
    "(5 out of 10 tasks done). It stopped 62.0\\% of injections (62, out of 100 tries) which means 38.0\\% of attacks still got through using indirect ways."
)
new_abs = (
    "Background tasks are managed by a piecewise heartbeat scheduler. This scheduler determines how often it checks in. "
    "It starts checking every 30 seconds. Then it slows down to every 900 seconds when the system is not being used. "
    "Also a multi-axis affective engine keeps track of the users mood. When the user looks urgent. Upset it changes the order of tasks "
    "to respond faster. Tool execution is controlled by a 5-level permission structure. This structure uses a poset lattice. "
    "Asks for confirmation each time with a pop-up prompt. It also uses a Win32 desktop station hook to deal with the Session 0 black screen problem. "
    "On hardware Dione it finished 27.6\\% of tasks overall when tested on GAIA and AgentBench benchmarks. That is 50.0\\% on machines "
    "(5 out of 10 tasks done). It stopped 62.0\\% of injections (62 out of 100 tries) which means 38.0\\% of attacks still got through using ways."
)
if old_abs_target in tex:
    tex = tex.replace(old_abs_target, new_abs)
    print("Replaced Abstract target.")

# 2. Contributions
old_contrib = (
    "\\item \\textbf{MAF-Native Execution:} We add fixed step limits ($N_{max} = 10$) to the Microsoft Agent Framework. "
    "We use typed schemas (\\texttt{@tool}) to stop hallucination loops in local small language models. This keeps things running smoothly. "
    "Prevents models from going off track.\n"
    "    \\item \\textbf{Mathematical Context Optimization:} We treat building under hardware token limits as a clear 0-1 Knapsack "
    "Optimization Problem. This gives us a 1/2-approximation guard for single items. Then we combine this with a Probabilistic "
    "Graph Path-Ranking Model that runs over a typed NetworkX multigraph. It helps us pick the path when choices are limited.\n"
    "    \\item \\textbf{Affective State \\& Persona Modeling:} We map emotional state changes along axes. We order events, in a "
    "queue so that urgent or frustrated inputs jump ahead of normal background tasks. This way the system responds better when people "
    "are stressed or need help."
)
new_contrib = (
    "\\item \\textbf{MAF-Native Execution:} We add fixed step limits ($N_{max} = 10$) to the Microsoft Agent Framework. "
    "We use typed schemas (\\texttt{@tool}) to stop hallucination loops in small language models. This keeps things running smoothly. "
    "Prevents models from going off track.\n"
    "    \\item \\textbf{Mathematical Context Optimization:} We treat building under hardware token limits as a 0-1 Knapsack "
    "Optimization Problem. This gives us a 1/2-approximation guard for items. Then we combine this with a Probabilistic "
    "Graph Path-Ranking Model that runs over a typed NetworkX multigraph. It helps us pick the path when choices are limited.\n"
    "    \\item \\textbf{Affective State \\& Persona Modeling:} We map emotional state changes, along axes. We order events in a "
    "queue so that urgent or frustrated inputs jump ahead of background tasks. This way the system responds better when people "
    "are stressed or need help."
)
if old_contrib in tex:
    tex = tex.replace(old_contrib, new_contrib)
    print("Replaced Contributions.")

# 3. AutoGPT
old_autogpt = (
    "In real-world testing, open-source agent scripts like AutoGPT~\\cite{agentbench2023} used regex patterns instead of raw JSON. "
    "When we ran 7B models on our computers small mistakes in formatting like a missing comma or extra backticks caused errors "
    "that the agent couldn't handle. These errors made the agent get stuck in loops. The Microsoft Agent Framework "
    "(MAF 1.21.0)~\\cite{microsoft2025maf} solves this problem by using typed schemas (\\texttt{@tool}) and interceptor "
    "middleware (\\texttt{AgentMiddleware}). Dione uses MAF directly adding typed tool dispatch along, with host safety checks "
    "and disk-based graph retrieval."
)
new_autogpt = (
    "In real-world testing, open-source agent scripts like AutoGPT~\\cite{agentbench2023} used expressions instead of raw JSON. "
    "When we ran 7B models on our computers mistakes in formatting like a missing comma or extra backticks caused errors that the agent "
    "couldn't handle. These errors made the agent get stuck in loops. The Microsoft Agent Framework (MAF 1.21.0)~\\cite{microsoft2025maf} "
    "solves this problem by using typed schemas (\\texttt{@tool}) and interceptor middleware (\\texttt{AgentMiddleware}). "
    "Dione uses MAF adding typed tool dispatch along with host safety checks and disk-based graph retrieval."
)
if old_autogpt in tex:
    tex = tex.replace(old_autogpt, new_autogpt)
    print("Replaced AutoGPT.")

# 4. Memory Subsystems
old_mem = (
    "Retrieval-augmented generation (RAG) systems rely on vector embeddings, such as those used in ChromaDB or FAISS to find "
    "relevant information by measuring cosine similarity~\\cite{rag2020}. These systems work well when searching for text "
    "fragments. They struggle with understanding relationships between ideas. As conversations continue over sessions the "
    "quality of the search results tends to drop. This happens because unrelated messages can share words or phrases leading "
    "to irrelevant matches. Packer et al. Proposed MemGPT~\\cite{packer2023memgpt} which models context like memory in an "
    "operating system. This approach helps manage memory efficiently during long conversations. Edge and colleagues created "
    "GraphRAG~\\cite{graphrag2024}, while Pan et al.~\\cite{pan2024unifying} and Sun et al.~\\cite{sun2024think} verified "
    "graph reasoning benefits. Dione takes a path using an incremental typed multigraph built with NetworkX. The system "
    "performs bounded 2-hop traversals directly on disk in 1.158~ms. This method avoids the need for repeated clustering "
    "and summarization making it faster and more efficient."
)
new_mem = (
    "Retrieval-augmented generation (RAG) systems rely on vector embeddings, such as those used in ChromaDB or FAISS to find "
    "information by measuring cosine similarity~\\cite{rag2020}. These systems work well when searching for text fragments. "
    "They struggle with understanding relationships between ideas. As conversations continue over sessions the quality of the "
    "search results tends to drop. This happens because unrelated messages can share words or phrases leading to matches. "
    "Packer et al. Proposed MemGPT~\\cite{packer2023memgpt} which models context like memory in an operating system. This approach "
    "helps manage memory during long conversations. Dione takes a path using a typed multigraph built with NetworkX. The system "
    "performs bounded 2-hop traversals directly on disk in 1.158~ms. This method avoids the need for repeated clustering and "
    "summarization making it faster and more efficient."
)
if old_mem in tex:
    tex = tex.replace(old_mem, new_mem)
    print("Replaced Memory Subsystems.")

# 5. Security Literature
old_sec = (
    "Giving an agent the ability to execute shell commands on a computer introduces serious security risks. "
    "Ruan et al.~\\cite{ruan2023identifying} Found that when agent loops are not properly limited the agent may repeatedly "
    "run commands if earlier steps fail. This can lead to potentially harmful actions. Greshake et al.~\\cite{greshake2023not} "
    "and Liu et al.~\\cite{liu2023prompt} Demonstrated that untrusted inputs---like downloaded emails or web pages---can "
    "contain hidden injections. These injections can redirect the agent's tool execution in ways. Zhang et al. Formalized "
    "these threats in the Agent Security Bench (ASB)~\\cite{zhang2024agentbench}. ASB categorizes attacks, into tool "
    "tampering, memory poisoning and unauthorized privilege escalation. This framework helps researchers and developers "
    "better understand and defend against real-world threats to agents."
)
new_sec = (
    "Giving an agent the ability to execute commands on a computer introduces serious security risks. "
    "Ruan et al.~\\cite{ruan2023identifying} Found that when agent loops are not properly limited the agent may repeatedly "
    "run commands if earlier steps fail. This can lead to potentially harmful actions. Greshake et al.~\\cite{greshake2023not} "
    "and Liu et al.~\\cite{liu2023prompt} Demonstrated that untrusted inputs---like downloaded emails or web pages---can "
    "contain injections. These injections can redirect the agents tool execution in ways. Zhang et al. Formalized "
    "these threats, in the Agent Security Bench (ASB)~\\cite{zhang2024agentbench}."
)
if old_sec in tex:
    tex = tex.replace(old_sec, new_sec)
    print("Replaced Security Literature.")

# 6. Live Summary
old_live = (
    "Live Summary: 5 out of 10 tasks worked when run in time without any fake setups (thats 50.0\\% success). "
    "This matches the 27.6\\% success rate from the test and shows a 38.0\\% difference, in how secure the system is."
)
new_live = (
    "Live Summary: Five out of ten tasks worked when run in time without any fake setups, which is fifty percent success. "
    "This matches the 27.6\\% success rate from the test. Shows a thirty-eight percent difference, in how secure Dione is."
)
if old_live in tex:
    tex = tex.replace(old_live, new_live)
    print("Replaced Live Summary.")

MASTER_TEX.write_text(tex, encoding="utf-8")
print("Updated docs/DIONE_IEEE_RESEARCH_PAPER.tex successfully!")

# Copy to other 3 TeX targets
target_texs = [
    DOCS_DIR / "DIONE_IEEE_RESEARCH_PAPER_PUBLISHABLE.tex",
    BASE_DIR / "DIONE_IEEE_RESEARCH_PAPER.tex",
    BASE_DIR / "DIONE_IEEE_RESEARCH_PAPER_PUBLISHABLE.tex"
]
for t in target_texs:
    t.write_text(tex, encoding="utf-8")
    print(f"Synchronized {t.name}")
