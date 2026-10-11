# 🎓 Dione AI — Official Teacher Demo Sequence & Viva Cheatsheet
**Group 19 (VESIT Computer Engineering, 2025–26)**  
**Project:** Dione — Privacy-Preserving Local Large Action Model (LAM) Orchestration Engine  
**Mentor:** Prof. Geocey Shejy | **HOD:** Dr. Mrs. Nupur Giri  

---

## 🚀 How to Launch the Demo in 1 Click
Double-click **`run_live_demo.bat`** on your desktop. It opens the master presentation menu:
* **Option `[1]`:** Guided Step-by-Step Live Teacher Demonstration *(Recommended)*
* **Option `[2]`:** Full Automated 10-Station Benchmark Walkthrough
* **Option `[3]`:** Open Live Interactive Chat Client (`dione client`)
* **Option `[4]`:** Open Black Book Report (.docx) and PowerPoint Slides (.pptx)

---

## 📋 The 8-Step Presentation Script for Your Teacher

### 1️⃣ Feature 1: Social Intelligence & Relationship Retention
* **What to Say to Teacher:**  
  *"Ma'am, existing conversational agents treat every conversation as a blank slate. Dione includes a dedicated Social Intelligence Engine that maintains persistent dossiers on colleagues and mentors. If I refer to you casually as 'mentor', 'Prof. Geocey', or 'Guide', Dione automatically disambiguates your identity and enforces academic respect."*
* **What to Show on Screen:**  
  Table showing canonical resolution of `Prof. Geocey Shejy`, your institutional email (`geocey.shejy@ves.ac.in`), and the mandatory formal academic salutation (`"Respected Ma'am,"`).

---

### 2️⃣ Feature 2: Automated Commitment & Promise Mining
* **What to Say to Teacher:**  
  *"When working on capstone projects, students make informal promises in chat that often get forgotten. Dione actively monitors conversation turns for commitments. For example, when I say: 'I promised Prof. Geocey to prepare the benchmark charts by 5 PM today', Dione mines this promise and attaches it directly to your node in the Knowledge Graph."*
* **What to Show on Screen:**  
  The NetworkX graph updating with an active `PROMISED_TO` edge connecting the deliverable to Prof. Geocey Shejy.

---

### 3️⃣ Feature 3: Live Web Research & Real-Time Page Scraping
* **What to Say to Teacher:**  
  *"Unlike static assistants, Dione has a live web research and scraping engine built using Python HTTP streaming and HTML sanitization. It can scrape any public URL and search arXiv for academic literature without relying on external cloud APIs."*
* **What to Show on Screen:**  
  Live scraping of real web content and arXiv search results for *"Large Action Models"* with clean summaries, links, and publication metadata.

---

### 4️⃣ Feature 4: Ambient Heartbeat & 1-Click Proactive Proposal Cards
* **What to Say to Teacher:**  
  *"Most AI agents are purely reactive—they only speak when spoken to. Dione features an Ambient Heartbeat that learns the user's hourly, daily, and weekly habits. On Monday at 9:00 AM, Dione automatically stages our weekly progress email to you, pulling in our active Chapter 6 commitments. But under our strict safety policy, Dione never sends emails autonomously without 1-click human approval."*
* **What to Show on Screen:**  
  The red-bordered **Proactive Proposal Card** with the auto-drafted email and the `[1] [Approve & Send] [2] [Edit Draft] [3] [Dismiss]` buttons.

---

### 5️⃣ Feature 5: 5-Tier Safety Kernel & Adversarial Injection Defense
* **What to Say to Teacher:**  
  *"Giving an AI agent desktop access introduces critical security risks. To address this, we implemented a 5-Tier Safety Kernel based on a permission lattice. If a malicious prompt tries to delete `system32` or run unauthorized shell commands, Dione intercepts the call, blocks execution, and records an audit log."*
* **What to Show on Screen:**  
  The Safety Kernel table showing `FilesystemPlugin.read_file` allowed (Tier 0 Safe Read), while `rmdir /s /q C:\Windows\System32` is blocked with Critical Risk.

---

### 6️⃣ Feature 6: Affective Sentiment & AI-Controlled Dynamic UI
* **What to Say to Teacher:**  
  *"Dione doesn't just respond with text—she adapts her persona and controls the UI. If the user expresses stress or panic before a deadline, Dione's sentiment analyzer detects the emotional distress, increases warmth, and dynamically generates glassmorphic UI directives for the frontend."*
* **What to Show on Screen:**  
  The emotional state transition and the generated UI directive (`#6C63FF` primary color, dark ambient lighting, and pulse animation).

---

### 7️⃣ Feature 7: Nighttime Deep Context Synthesis ("Dream Mode")
* **What to Say to Teacher:**  
  *"When the user is away or asleep, Dione enters 'Dream Mode'. She scans active project nodes, researches related concepts in the background, and pre-compiles context into the offline graph so the student gets sub-2ms instant responses the next morning."*
* **What to Show on Screen:**  
  The Dream Synthesis report showing scanned nodes, new knowledge nodes created, and offline context summaries.

---

### 8️⃣ Feature 8: Workstation Host Footprint & Zero Cloud Leak
* **What to Say to Teacher:**  
  *"Finally, Ma'am, Dione runs entirely on consumer hardware. We're actively profiling it using `psutil`: it consumes only ~54 MB to 463 MB of RAM, and all graph lookups complete in 1.158 ms with zero data transmitted to third-party cloud servers."*
* **What to Show on Screen:**  
  The live hardware verification table confirming 100% on-device execution.

---

## 🎯 Likely Teacher Questions & Winning Answers

* **Q: How does Dione differ from LangChain or AutoGPT?**  
  * **Answer:** *"LangChain and AutoGPT are cloud-dependent frameworks that suffer from context bloat and runaway token consumption. Dione is a 100% local Large Action Model with deterministic step budgets, an in-memory NetworkX Knowledge Graph that saves ~75% tokens, and an interactive confirmation gate that prevents unapproved actions."*

* **Q: Where is the Knowledge Graph stored?**  
  * **Answer:** *"It is persisted as a directed multigraph $G=(V, E, \mathcal{R})$ in `data/knowledge/graph.json` and loaded into high-speed NetworkX memory at runtime, yielding 1.158 ms 2-hop subgraph queries."*

* **Q: Can Dione send emails or delete files by itself?**  
  * **Answer:** *"No, Ma'am. Our 5-Tier Safety Kernel strictly prohibits autonomous execution of mutating actions. Dione generates staged 1-Click Proposal Cards, requiring explicit human authorization before any external API is touched."*
