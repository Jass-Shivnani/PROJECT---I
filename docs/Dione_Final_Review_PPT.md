# **VESIT \- V.E.S.**

## **Dione Ai : An AI Personal Assistant**

**Inhouse Project : 2025-26**

**Review \- II**

**Team Members:**

1. Jass Shivnani D12B(50)  
2. Riya Khialani D12A(34)  
3. Khushi Sadhuramani D12B(44)  
4. Ruchika Dingria D12B(70)

**Group Number:** 19

**Project Mentor:** Mrs. Geocey Shejy

**SDG-8:** Decent work & Economic growth

## **Content**

i. Introduction to Project

ii. Lacuna in the existing systems

iii. Problem Definition

iv. Literature Survey

v. Methodology employed

vi. Hardware, Software, tools and the constraints

vii. Block Diagram

viii. Modular Diagram

ix. Figma / UI

x. Implementation (work done)

xi. Next Work Plan

xii. Conclusion

xiii. References

## **Introduction to Project**

**\[Image Description: Dione AI Conceptual Hub Diagram\]**

*A visual diagram illustrating Dione AI as a central hub connecting the user to various functionalities and applications.*

* *At the top, a "User" icon points down into the glowing central "Dione AI" core.*  
* *Arrows radiate outwards from the center to four main capability pillars:*  
  1. ***Personal Data & Commands:*** *Runs on User Device (represented by a security lock icon).*  
  2. ***Manages Tasks & Apps:*** *(represented by a checklist and computer monitor).*  
  3. ***Converts Commands to Actions:*** *(represented by a clipboard and pen).*  
  4. ***Executes Actions Locally:*** *(represented by gears and the Gmail 'M' logo).*  
* *Between these pillars, Dione connects directly to popular cloud apps: Instagram, WhatsApp, Gmail, and Slack workflows.*

## **Introduction to Project**

**Dione AI \- Intelligent Action-Based Personal Assistant**

**What is Dione AI?**

Dione AI is an assistant that understands user commands, interprets intent, and converts it into meaningful actions across apps and services.

**What It Does**

* Understands natural language instructions  
* Connects with apps like Gmail, WhatsApp, Instagram, Slack, etc.  
* Automates tasks such as sending messages, organizing info, scheduling, and more  
* Helps manage day-to-day digital activities efficiently

**Why It Matters**

* Provides a unified interface to interact with multiple apps  
* Reduces manual work through automated actions  
* Enhances productivity with intelligent decision-making  
* Designed for ease of use and real-world task handling

*Dione AI \= Intelligent. Action-Driven. Helpful.*

## **LACUNA IN THE EXISTING SYSTEM**

**\[Image Description: Icons representing the flaws of current systems\]**

*A slide containing five icons with corresponding text highlighting the drawbacks of current AI assistants:*

1. **Cloud-dependent AI:** *(Icon of a cloud)*  
2. **Limited personalization:** *(Icon of a person with sliders/settings)*  
3. **Privacy risks:** *(Icon of a finger pressing a 'Private' toggle switch)*  
4. **No local execution:** *(Icon of a laptop with a red 'prohibited' sign over the screen)*  
5. **Fragmented tools:** *(Icon of a puzzle piece with a wrench inside)*

## **Problem Statement**

**\[Image Description: Digital Overload Illustration\]**

*An illustration of a stressed and overwhelmed person sitting at a laptop (which has a privacy shield on the screen). Surrounding the user are floating icons representing digital chaos: urgent emails (Gmail), overflowing calendars, pending tasks, scattered files, notification badges (35, 15, 7, 4), messaging apps (Telegram/Paper plane), and a ticking 12-hour clock. The surrounding graphical icons emphasize:*

* *Busy digital life*  
* *No unified assistance*  
* *Low productivity*  
* *Missed reminders & tasks*  
* *Manual task execution*  
* *Time-consuming workflows*

## **Problem Statement**

* **Modern users face a highly fragmented digital ecosystem** with multiple apps, notifications, and platforms.  
* **This leads to:**  
  * Cognitive overload due to constant interruptions  
  * Lack of a centralized assistant to manage tasks across platforms  
  * Reduced productivity and inefficient time utilization  
* **Key challenges:**  
  * Missed reminders and important tasks  
  * Heavy reliance on manual task execution  
  * Time-consuming workflows across different applications  
* **Overall impact:**  
  * Users struggle to manage, prioritize, and act efficiently in their daily digital lives

## **Literature Survey**

| Year | Paper Title | Authors & Affiliations | Focus Area | Qualitative Analysis | Quantitative Analysis | Key Limitations |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **2025** | A Novel Local Agent-Based AI LLM with RL and Advanced Reasoning Capabilities for Management Support | Jovan Ivković, ITS Visoka škola strukovnih studija za IT, Serbia; Jelena Lužija Ivković | Local Agentic AI, RL-based Management Reasoning | Strong hybrid LLM \+ RL framework enabling autonomous reasoning and decision-making support | Evaluates RL optimization accuracy, reasoning clarity, and decision performance | High computational cost; RL training complexity; limited deployment scenarios |
| **2024** | TauchiGPT\_V2: An Offline Agent-Based Open-Source AI Tool Designed to Assist in Academic Research | Ahmed Farooq, Jari Kangas (Tampere University); Mounia Ziat (Bentley University); Roope Raisamo (Tampere University) | Offline AI Assistant, Academic Agent Systems | Demonstrates practical offline LLMbased \-agent for academic tasks; strong usability in text analysis | Measures offline accuracy, latency, and task completion efficiency | Less accurate than cloud LLMs; limited by hardware and dataset scale |
| **2026** | AI-Driven Explicit and Implicit Information Collection in Requirements Engineering: Classification and Knowledge Representation | Ahmad Murad, Khalil Ahmad Mahmoud Jamous (Al-Quds University); Ihab Atieh, Amjad Hudaib (University of Jordan) | Requirements Engineering, Knowledge Representation | Strong conceptual framework for using AI to classify and extract explicit & implicit requirements; enhances clarity and requirement traceability | Contains model evaluation metrics such as classification accuracy and comparative performance | Limited dataset variety; focuses on conceptual modeling rather than large-scale real-world deployment |
| **2024** | In Prospect and Retrospect: Reflective Memory Management for Long-term Personalized Dialogue Agents | Zhen Tan, Jun Yan, I-Hung Hsu, Rujun Han, Zifeng Wang, Long T. Le, Yiwen Song, Yanfei Chen, Hamid Palangi, George Lee, Google Cloud AI; Anand Iyer, Google Cloud AI; Tianlong Chen, UNC Chapel Hill; Huan Liu, ASU; Chen-Yu Lee, Google Cloud AI; Tomas Pfister, Google Cloud AI | Long-term Memory for LLM Agents | Introduces reflective memory updates, enabling long-term personalization and continuous contextual reasoning | Evaluates memory retention, retrieval accuracy, and personalization efficiency | Memory overhead; optimization complexity; challenging real-world implementation |
| **2024** | SuperAgent: A Scalable Multi-Agent Framework for Autonomous Task Execution Using Large Language Models | Yash Malsuare, Aryan Purohit, Isha Syed, Dr. Maheshwari Birada (DY Patil International University) | Multi-Agent Systems, Autonomous Task Execution | Demonstrates scalable multi-agent coordination using LLMs; simplifies workflow automation | Performance measured through distributed task execution, coordination time | Limited benchmarks; early-stage experimentation; generalization issues |

## **Methodology**

**\[Image Description: Methodology Flowchart\]**

*A linear flowchart illustrating the system methodology:*

1. **USER** inputs a *Natural language command*.  
2. The command is sent to the **AI LLM**.  
3. The LLM feeds into the **Dione engine**, which *Interprets user intent*.  
4. The engine formulates an *Action plan*.  
5. The system moves to the next step where the **Plugin selects required tool/API**.  
6. The tool/API interfaces with the **Local system** to execute the task.  
7. Finally, **Feedback** is sent back to the USER.

## **Hardware, Software, Tools and constraint**

**Hardware Requirements**

* Laptop/PC with 8-16 GB RAM  
* Quad-core CPU (i5/Ryzen 5 or above)  
* SSD storage  
* Optional GPU for faster model performance  
* Smartphone (Android/iOS) for the mobile companion app

**Software Requirements**

* Python 3.10+  
* Ollama / llama.cpp (for running local LLMs)  
* FastAPI (backend API)  
* Flutter (mobile app)  
* ChromaDB (vector memory)  
* Internal Knowledge Graph system (custom Python modules)

## **Hardware, Software, Tools and constraint**

**Tools Used**

* Local LLMs (Llama models)  
* ReAct-based Orchestration Engine  
* Sentiment Analysis Engine  
* Plugin System (Gmail, WhatsApp, Calendar, Filesystem, Browser)  
* Git/GitHub for version control

**Constraints**

* Dependent on local hardware performance  
* Larger LLMs cannot run smoothly on low-end devices  
* Knowledge graph \+ vector memory consume storage over time  
* Mobile app needs connection to local server  
* No cloud support → heavy tasks run slower locally  
* Security of data depends on user's device

## **Block Diagram**

**\[Image Description: Dione AI System Block Diagram\]**

*A detailed architectural diagram showing how data moves between local resources and the LLM.*

* **User Input:** Natural language flows into the *Local LLM Reasoning Engine*.  
* **Local LLM Reasoning Engine:** Generates *structured commands* and passes them to the *Modular Plugin Orchestration* block.  
* **Modular Plugin Orchestration:** Contains a *Plugin Interface* which directs commands to specific *Plugins* (Calendar Plugin, Email Client Plugin, Messaging Plugin, File System Plugin).  
* **Local Applications:** The respective plugins send and receive *data* from the actual *Local Applications* (Calendar Tool, Email Client, Messaging Platform, File System). The plugins then return *processed data* back through the interface, which formulates a *response* back to the user.

## **Modular Diagram**

**\[Image Description: Dione System Modular Architecture\]**

*A detailed view of the system modules and their interactions (identical to the diagram in the project report).*

* **User Interface:** Chat Interface accepts natural language.  
* **Dione Core Engine:** Uses a Request Parser and Response Generator.  
* **Local LLM:** Features a Reasoning Engine and Context Manager.  
* **Local Data Store:** Stores User Preferences, Message Database, and Action History. Supplies data to the Context Manager.  
* **Plugin Interface:** Contains a Plugin Registry, API Standardization Layer, and Execution Sandbox. Connects to the plugins.  
* **Plugins:** Communication Plugins (WhatsApp, iMessage, Gmail) and Productivity Plugins (Calendar, File System, Notes).

## **Figma / UI**

**\[Image Description: Command Line Interface (CLI) Screenshot\]**

*A terminal window demonstrating Dione executing a local file creation task based on a natural language prompt.*

**\[OCR Extracted Text from CLI\]:**

PS C:\\Users\\Jass\\Documents\\CAPSTONE PROJECT I\>./dione client  
DIONE  
v0.2.0-Interactive Client  
Connected to \[http://127.0.0.1:8000\](http://127.0.0.1:8000)  
Server v0.2.0 copilot/gpt-4-mini  
Type a message to chat, or /help for commands. Ctrl+C to exit.

You: can you create a folder at desktop named "Jass capstone" and make a hello.txt file inside it write "Me esa kyu hu"

Dione: Done \- created C:\\Users\\Jass\\Desktop\\Jass capstone\\hello.txt with content: "Me esa kyu hu". Anything else you want done? By the way, what should I call you?  
\[95312ms | tools: SystemPlugin.run\_command, FileSystemPlugin.write\_file\]

## **Figma / UI**

**\[Image Description: File Explorer and Text Editor Screenshot\]**

*A screenshot validating the action taken by the CLI in the previous slide. It shows a Windows File Explorer window open to C:\\Users\\Jass\\Desktop\\Jass capstone. Inside the folder is a single file named hello.txt. Overlaid on top is an open Notepad window showing the contents of hello.txt.*

**\[OCR Extracted Text from Notepad\]:**

Me esa kyu hu

## **Implementation**

**\[Image Description: CLI and Mobile WhatsApp Screen\]**

*A split view showing the CLI on the left executing a WhatsApp command, and a mobile phone screen on the right showing the actual WhatsApp application successfully sending the message.*

**\[OCR Extracted Text from CLI\]:**

Waiting for server...  
Server is running  
API: \[http://0.0.0.0:8000/api\](http://0.0.0.0:8000/api)  
...  
Run dione client to start chatting  
Run dione stop to stop the server

PS C:\\Users\\Jass\\Documents\\CAPSTONE PROJECT I\>./dione client  
DIONE  
v0.2.0-Interactive Client  
...  
You: send hi to \+919699749462 on whatsapp  
\[Dione is thinking...\]  
\[60219ms | tools: whatsapp\_send\]

**\[Visual Description of Phone Screen\]:**

*A WhatsApp chat window with the contact "Chandni Son...". The last sent message is a green chat bubble containing "hi" sent at 1:02 am.*

## **Implementation**

**\[Image Description: CLI executing Gmail Read and Send commands\]**

*A terminal window demonstrating Dione reading the latest email and then drafting/sending a new email based on user intent.*

**\[OCR Extracted Text from CLI\]:**

You: read latest mail on gmail  
Dione (curious): Latest email \- From: Google \<no-reply@accounts.google.com\> Subject: Security alert Date: Tue, 24 Mar 2026 18:24:09 GMT Preview: "A sign-in attempt was blocked for your account... If you didn't generate this password for Dione, someone might be using your account. Check and secure your account immediately...  
\[52016ms | tools: gmail\_read\]

You: send mail to riyakhialani@gmail.com and introduce urself  
\[Dione is thinking...\]

## **Implementation**

**\[Image Description: Gmail Web Interface Screenshot\]**

*A screenshot of a desktop web browser showing the sent email inside Gmail, validating the CLI command from the previous slide.*

**\[OCR Extracted Text from Email Body\]:**

Subject: Introduction \- Dione (personal AI assistant)  
From: jassshivnani11@gmail.com  
To: me (Riya)

Hi Riya,

I'm Dione \- Jass Shivnani's personal AI assistant. I help with software development tasks like code review, debugging, writing and running scripts, automating workflows, drafting docs, and scheduling. I can generate code snippets, run commands with Jass's approval, and help keep projects moving.

If you'd like to collaborate or have any questions, please reply here or to Jass.

Best,  
Dione (on behalf of Jass)

## **Implementation**

**Core Implementation \- Dione Orchestration Engine (ReAct Architecture)**

* **Central brain of the system** handling reasoning and decision-making  
* **Implements ReAct Loop:**  
  * Think → Retrieve → Decide → Act → Learn  
* **Integrates:**  
  * Context Manager (chat \+ memory)  
  * Knowledge Graph (entity relationships)  
  * Sentiment Engine (priority understanding)  
* **Uses local LLM** (Mistral/LLaMA) for:  
  * Thought generation  
  * Action selection (tool usage)  
* **Supports multi-step reasoning and autonomous execution**

**Flow:**

User Input → Context Building → LLM Reasoning → Tool Selection → Execution → Response

*"Transforms user queries into intelligent, context-aware actions"*

## **Implementation**

**Memory, Knowledge & Action Layer**

**Knowledge Graph**

* Stores structured data (People, Events, Documents)  
* Enables contextual understanding via relationships

**Memory System (RAG)**

* Uses embeddings \+ vector database (ChromaDB)  
* Retrieves relevant past information dynamically

**Sentiment Intelligence**

* Detects emotion, urgency, and importance  
* Prioritizes responses accordingly

**Plugin System**

* Executes real-world actions (Gmail, WhatsApp, Files)  
* Secure via permission control \+ sandboxing

**Flow:**

Query → Graph \+ Memory Retrieval → Sentiment Analysis → Action via Plugins

*"Combines memory, emotion, and actions to create a truly intelligent assistant"*

## **Next Work Plan**

1. **Advanced Personalization**  
   * Enhance knowledge graph with deeper behavioral learning  
   * Adaptive responses based on long-term user habits  
2. **Multimodal Intelligence**  
   * Support for voice, images, and documents  
   * Voice assistant integration for hands-free interaction  
3. **Cross-Device Synchronization**  
   * Secure syncing across multiple user devices  
   * Maintain privacy using encrypted peer-to-peer transfer  
4. **Smarter Agent Automation**  
   * Enable fully autonomous task execution and make the agent self-repairing  
   * Multi-agent collaboration for complex workflows

*"Evolving Dione into a fully autonomous, privacy-first digital companion across all aspects of life."*

## **Conclusion**

Dione reimagines the future of AI assistants by shifting intelligence from the cloud to the user's device. It combines local LLMs, knowledge graphs, sentiment analysis, and agentic execution to create a system that not only responds, but understands, reasons, and acts.

By ensuring complete data privacy, contextual awareness, and real-world task automation, Dione overcomes the limitations of traditional cloud-based assistants. Its modular and extensible architecture allows it to evolve into a truly personalized digital companion.

Dione is not just an assistant \- it is a step toward human-centric, sovereign AI systems that empower users while respecting their privacy.

*"Dione doesn't just assist \- it thinks, remembers, and acts with you, entirely on your terms."*

## **References**

* “A Novel Local Agent-Based AI LLM with RL and Advanced Reasoning Capabilities for Management Support,” 2025\. Available: ResearchGate.  
* "Agentic AI: A Review, Applications, and Open Research Challenges,” 2025\. Available: ResearchGate.  
* “TauchiGPT V2: An Offline Agent-Based Open-Source AI Tool Designed to Assist in Academic Research,” 2024\.  
* Shunyu Yao et al., “ReAct: Synergizing Reasoning and Acting in Language Models,” 2023\.  
* OpenAI, “GPT-4 Technical Report,” 2023\.  
* Tom Brown et al., “Language Models are Few-Shot Learners,” 2020\.  
* Meta AI, “LLaMA: Open and Efficient Foundation Language Models,” 2023\.