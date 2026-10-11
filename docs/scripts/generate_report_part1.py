"""Part 1: Setup, Front Matter, Chapter 1 (Expanded)"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

FONT = 'Times New Roman'
doc = Document()
for s in doc.sections:
    s.top_margin=Cm(2.54); s.bottom_margin=Cm(2.54); s.left_margin=Cm(3.17); s.right_margin=Cm(2.54)
st=doc.styles['Normal']; st.font.name=FONT; st.font.size=Pt(12)
st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; st.paragraph_format.space_after=Pt(6); st.paragraph_format.line_spacing=1.5

def h1(t):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(t.upper()); r.bold=True; r.font.size=Pt(20); r.font.name=FONT
    p.paragraph_format.space_before=Pt(24); p.paragraph_format.space_after=Pt(12)
def h2(t):
    p=doc.add_paragraph(); r=p.add_run(t); r.bold=True; r.font.size=Pt(16); r.font.name=FONT
    p.paragraph_format.space_before=Pt(18); p.paragraph_format.space_after=Pt(8)
def h3(t):
    p=doc.add_paragraph(); r=p.add_run(t); r.bold=True; r.font.size=Pt(14); r.font.name=FONT
    p.paragraph_format.space_before=Pt(12); p.paragraph_format.space_after=Pt(6)
def body(t):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    r=p.add_run(t); r.font.size=Pt(12); r.font.name=FONT; p.paragraph_format.line_spacing=1.5
def ct(t,sz=12,b=False):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(t); r.bold=b; r.font.size=Pt(sz); r.font.name=FONT
def ip(c):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(f'[Image Placeholder: {c}]'); r.italic=True; r.font.size=Pt(11); r.font.name=FONT; r.font.color.rgb=RGBColor(128,128,128)
def pb(): doc.add_page_break()
def tbl(headers,rows):
    t=doc.add_table(rows=len(rows)+1,cols=len(headers)); t.style='Table Grid'
    for j,h in enumerate(headers): t.cell(0,j).text=h
    for i,row in enumerate(rows):
        for j,val in enumerate(row): t.cell(i+1,j).text=val

# ============ TITLE PAGE ============
ct("VIVEKANAND EDUCATION SOCIETY'S INSTITUTE OF TECHNOLOGY",14,True)
ct("(An Autonomous Institute Affiliated to University of Mumbai)",12)
ct("Department of Computer Engineering",14,True)
doc.add_paragraph(); ip("College Logo"); doc.add_paragraph()
ct("Project Report on",14); ct("DIONE",24,True)
ct("A Local Large Action Model (LAM) Orchestration Engine",14)
doc.add_paragraph()
ct("In partial fulfillment of the Third Year (Semester-VI),",12)
ct("Bachelor of Technology (B.Tech.) Degree in Computer Engineering",12)
ct("at the University of Mumbai, Academic Year 2025-26",12)
doc.add_paragraph()
ct("Project Mentor: Prof. Geocey Shejy",12,True); doc.add_paragraph()
ct("Submitted by",12,True)
for n in ["Riya Khialani  D12A, 34","Jass Shivnani  D12B, 50","Khushi Sadhuramani  D12B, 44","Ruchika Dingria  D12B, 70"]: ct(n)
ct("(2025-26)",12,True); pb()

# ============ CERTIFICATE ============
h1("Certificate of Approval")
body('This is to certify that Riya Khialani (D12A), Jass Shivnani (D12B), Khushi Sadhuramani (D12B), and Ruchika Dingria (D12B) of Third Year Computer Engineering studying under the University of Mumbai have satisfactorily presented the project on \u201cDione \u2013 A Local Large Action Model (LAM) Orchestration Engine\u201d as a part of the coursework of CAPSTONE PROJECT \u2013 I for Semester-VI under the guidance of Prof. Geocey Shejy in the year 2025-26.')
doc.add_paragraph(); ct("Date: _______________"); doc.add_paragraph()
tbl(["Internal Examiner","External Examiner"],[["___________________","___________________"]])
doc.add_paragraph()
tbl(["Project Mentor","Head of Department","Principal"],[["___________________","Dr. Mrs. Nupur Giri\n___________________","Dr. J. M. Nair\n___________________"]]); pb()

# ============ DECLARATION ============
h1("Declaration")
body('We declare that this written submission represents our ideas in our own words and where others\u2019 ideas or words have been included, we have adequately cited and referenced the original sources. We also declare that we have adhered to all principles of academic honesty and integrity and have not misrepresented or fabricated or falsified any idea, data, fact, or source in our submission. We understand that any violation of the above will be cause for disciplinary action by the Institute and can also evoke penal action from the sources which have thus not been properly cited or from whom proper permission has not been taken when needed.')
doc.add_paragraph(); ct("Date: _______________"); pb()

# ============ ACKNOWLEDGEMENT ============
h1("Acknowledgement")
body('We are thankful to our college Vivekanand Education Society\u2019s Institute of Technology for considering our project and extending help at all stages needed during our work of collecting information regarding the project.')
body('It gives us immense pleasure to express our deep and sincere gratitude to Professor Geocey Shejy (Project Guide) for her kind help and valuable advice during the development of the project synopsis and for her guidance and suggestions.')
body('We are deeply indebted to the Head of the Computer Department, Dr. (Mrs.) Nupur Giri, and our Principal, Dr. (Mrs.) J. M. Nair, for giving us this valuable opportunity to do this project.')
body('We express our hearty thanks to them for their assistance without which it would have been difficult in finishing this project synopsis and project review successfully.')
body('We convey our deep sense of gratitude to all teaching and non-teaching staff for their constant encouragement, support, and selfless help throughout the project work. It is a great pleasure to acknowledge the help and suggestions which we received from the Department of Computer Engineering.')
body('We wish to express our profound thanks to all those who helped us in gathering information about the project. Our families too have provided moral support and encouragement several times.'); pb()

# ============ COURSE OUTCOMES ============
h1("Course Outcomes for Capstone Project")
body("Learners will be able to:")
tbl(["Course Outcome","Description"],[
    ("CO1","Identify and define a real-world problem through systematic requirement analysis and investigation."),
    ("CO2","Conduct a thorough literature review and benchmarking to propose innovative solutions."),
    ("CO3","Develop a structured project plan with well-defined milestones, timelines, and risk mitigation strategies."),
    ("CO4","Design and implement a working prototype using appropriate engineering tools and methods."),
    ("CO5","Analyze experimental results, validate the solution, and optimize performance based on data."),
    ("CO6","Effectively document and present the project outcomes, demonstrating professional ethics, teamwork, and project management skills."),
]); pb()

# ============ ABSTRACT ============
h1("Abstract")
body('The rapid advancement of Large Language Models (LLMs) has significantly enhanced the ability of artificial intelligence systems to understand, generate, and reason over human language. Models such as GPT-4, LLaMA, and Mistral have demonstrated impressive performance across a wide range of tasks, including text generation, summarization, translation, and complex reasoning. However, these models remain fundamentally limited in their functionality as they operate primarily within isolated chat interfaces. While they can suggest solutions or generate outputs, they lack the capability to execute real-world digital actions, creating a critical limitation known as the Actuation Gap. This disconnect restricts AI systems from transitioning beyond passive assistants to truly autonomous agents that can independently carry out tasks on behalf of the user.')
body('To address this limitation, this project introduces Dione, a Local Large Action Model (LAM) Orchestration Engine designed to enable secure and autonomous execution of tasks. Unlike existing cloud-based agentic AI systems such as AutoGPT and LangChain agents that require sensitive user data to be transmitted to external servers, Dione operates entirely on the user\u2019s local device. It acts as an intelligent middleware that bridges the reasoning capabilities of local LLMs with system-level tools, APIs, and applications. By converting unstructured model outputs into structured, executable commands, Dione enables AI to perform multi-step workflows such as retrieving data from local file systems, processing information through various pipelines, sending emails via Gmail API, managing calendar events, and triggering actions across different platforms and applications.')
body('The proposed system emphasizes a privacy-first, modular, and secure architecture built on principles such as zero-trust local inference, sandboxed plugin execution, and complete data sovereignty. Through its micro-kernel design and ReAct-based operational loop, Dione ensures efficient task execution while maintaining strict control over user data. The system incorporates a Context Manager powered by ChromaDB for maintaining conversational memory, a Model Adapter for seamless integration with multiple LLM backends, a Plugin Registry for dynamic tool management, and a Safety Guardrail module for preventing unauthorized or dangerous operations. This project demonstrates that it is possible to build powerful agentic AI systems without compromising privacy, thereby paving the way for the next generation of intelligent, user-controlled digital assistants.')
pb()

# ============ TABLE OF CONTENTS ============
h1("Table of Contents")
body("[Table of Contents \u2013 To be generated automatically in the final Word document using Insert > Table of Contents > Automatic Table.]"); pb()

# ============ CHAPTER 1: INTRODUCTION ============
h1("Chapter 1: Introduction")
body('This chapter introduces the concept, background, and motivation behind the proposed system, Dione \u2013 a Local Large Action Model (LAM) Orchestration Engine. It highlights the limitations of existing AI systems, defines the problem being addressed, establishes the relevance of the project in the current technological landscape, and outlines the methodology adopted to develop a secure, privacy-first agentic AI system. The chapter provides the necessary context for understanding the significance of the project and sets the stage for the detailed technical discussions that follow in subsequent chapters.')

h2("1.1 Introduction to the Project")
body('The rapid evolution of Artificial Intelligence over the past decade has led to the development of Large Language Models (LLMs) capable of performing advanced reasoning, natural language understanding, and content generation at unprecedented levels of sophistication. Models such as OpenAI\u2019s GPT-4, Meta\u2019s LLaMA 2, and Mistral 7B have demonstrated the ability to engage in complex conversations, answer domain-specific questions, generate code, summarize lengthy documents, and even perform mathematical and logical reasoning tasks with remarkable accuracy. These advancements have been made possible through innovations in transformer architectures, attention mechanisms, and large-scale pre-training on diverse text corpora.')
body('Despite these impressive advancements, such models are inherently limited in their functionality as they operate within isolated environments, primarily restricted to chat-based interactions. A user may ask an AI model to draft an email, organize files, or schedule a meeting, and the model can provide detailed instructions or generate the required text. However, the model itself cannot perform the action \u2013 it cannot open the email client, compose and send the email, navigate the file system, or interact with the calendar application. This fundamental limitation creates what researchers have termed the \u201cActuation Gap\u201d \u2013 the disconnect between an AI system\u2019s ability to reason about actions and its ability to actually execute them in the real world.')
body('To overcome this limitation, the proposed system, Dione, is designed as a Local Large Action Model (LAM) Orchestration Engine. It acts as an intermediary layer that bridges the gap between the reasoning capabilities of LLMs and the execution capabilities of system-level tools and applications. The name \u201cDione\u201d is inspired by the moon of Saturn, symbolizing a system that orbits around and augments a larger body \u2013 in this case, the LLM. By translating unstructured outputs from the model into structured, executable commands using JSON schemas, Dione enables the automation of real-world digital tasks. These tasks include but are not limited to retrieving and manipulating files on the local file system, composing and sending emails through the Gmail API, reading and responding to messages on WhatsApp, managing calendar events, executing system commands, and interacting with web browsers and other applications.')
body('The system is designed to operate entirely on the user\u2019s local device, eliminating the need for cloud-based processing and ensuring complete data privacy. This local-first approach is a key differentiator from existing agentic AI solutions such as AutoGPT, BabyAGI, and LangChain-based agents, which typically rely on cloud APIs and require users to share sensitive credentials and personal data with external servers. By keeping all data and processing local, Dione provides users with full control over their information and reduces the attack surface for potential security breaches.')

h2("1.2 Motivation for the Project")
body('The primary motivation behind this project arises from the inherent limitation of current AI systems, which are capable of reasoning but incapable of acting. This creates a dependency on users to manually execute tasks even after receiving accurate guidance from AI models. For instance, a user might ask an AI assistant to help organize their schedule for the week. The AI can generate a detailed plan, but the user must then manually enter each event into their calendar application, send reminder emails to participants, and set up necessary documents \u2013 a process that is time-consuming and defeats the purpose of having an AI assistant in the first place.')
body('Additionally, existing agentic AI systems that attempt to bridge this gap rely heavily on cloud-based architectures. Systems like AutoGPT and various LangChain-based agents require users to provide API keys for services like OpenAI, which means that every interaction, every piece of personal data, and every command passes through external servers. This introduces significant concerns related to privacy, security, and data ownership. Users must trust that their sensitive information \u2013 including email contents, personal documents, financial data, and authentication credentials \u2013 will be handled responsibly by third-party service providers. Recent incidents of data breaches and unauthorized data usage by AI companies have further amplified these concerns.')
body('Furthermore, the reliance on cloud infrastructure introduces several practical limitations. Internet connectivity becomes a prerequisite for any AI-assisted task, making the system unreliable in environments with poor or no network access. Latency issues arise from the round-trip time required to send data to remote servers and receive processed results. Cloud-based services often impose rate limits and usage quotas that restrict the number and frequency of API calls, limiting the system\u2019s throughput. Subscription costs for premium AI services create financial barriers that may exclude individual users and small organizations from accessing advanced AI capabilities.')
body('The motivation of this project is therefore to develop a local-first AI system that not only performs intelligent reasoning but also executes tasks autonomously while ensuring complete data privacy and user control. Dione aims to demonstrate that it is possible to build a fully functional agentic AI system that operates without any dependency on cloud infrastructure, using only locally deployed language models and locally executed plugins. This approach aligns with the growing movement toward edge computing and decentralized AI, where processing occurs closer to the data source rather than in centralized cloud data centers.')

h2("1.3 Drawbacks of Existing Systems")
body('Current implementations of AI-driven assistants and agent frameworks suffer from several critical limitations that collectively hinder their adoption and effectiveness. A thorough analysis of existing systems reveals the following key drawbacks that the proposed system, Dione, seeks to address.')
body('First, most existing systems are cloud-dependent, requiring all user data to be transmitted to and processed on remote servers. This architectural choice means that sensitive information such as personal emails, documents, browsing history, and authentication tokens are exposed to third-party infrastructure during processing. Even with encryption in transit, data is typically decrypted on the server side for processing, creating windows of vulnerability. High-profile data breaches at major technology companies have demonstrated that even sophisticated security measures cannot guarantee the protection of user data stored on remote servers.')
body('Second, these systems often require the storage of high-privilege credentials such as API tokens, OAuth keys, and service account passwords on centralized platforms. This concentration of authentication credentials makes these platforms attractive targets for cyberattacks. A single breach can compromise the credentials of thousands or millions of users simultaneously. The practice of storing credentials on third-party servers also raises questions about data governance and compliance with regulations such as the General Data Protection Regulation (GDPR) and the California Consumer Privacy Act (CCPA).')
body('Third, the dependency on internet connectivity introduces latency and reduces system reliability. In scenarios where network conditions are poor or unavailable, cloud-dependent AI assistants become completely non-functional. This limitation is particularly problematic for users in remote areas, those working in secure environments that restrict internet access, and situations where network disruptions occur due to natural disasters or infrastructure failures. The round-trip time required for cloud processing also adds noticeable delay to interactions, degrading the user experience.')
body('Fourth, existing systems lack true autonomy in task execution. While they can handle simple, single-step operations such as answering a question or generating text, they struggle with complex, multi-step workflows that require sequential actions, conditional logic, and error handling. For example, a task like \u201cfind the most recent invoice in my downloads folder, extract the amount due, and send a reminder email to the vendor\u201d requires multiple coordinated actions across different applications, with each step dependent on the successful completion of the previous one. Current systems typically lack the orchestration capabilities needed to manage such workflows reliably.')
body('Fifth, vendor-imposed restrictions and alignment policies further limit the flexibility and usability of cloud-based AI systems. Many commercial AI providers implement content filtering, usage policies, and output restrictions that prevent the model from performing certain types of tasks or generating certain types of content. While these restrictions serve important safety purposes, they can also prevent legitimate use cases and reduce the system\u2019s utility for power users who need unrestricted access to AI capabilities for professional or research purposes.')

h2("1.4 Problem Definition")
body('The problem addressed in this project is the inability of current AI systems to bridge the gap between reasoning and execution while maintaining user privacy and system security. Specifically, the project identifies and addresses the following core challenges.')
body('The primary challenge is the Actuation Gap \u2013 the fundamental disconnect between an AI model\u2019s ability to understand and reason about tasks and its ability to actually execute those tasks in the user\u2019s digital environment. Current LLMs can generate detailed plans, write code, and provide step-by-step instructions, but they cannot interact with the user\u2019s operating system, applications, or services to carry out the planned actions. This gap significantly limits the practical utility of AI assistants and creates a bottleneck in human-AI collaboration workflows.')
body('The secondary challenge is the Privacy-Security Paradox \u2013 the conflict between the need for AI systems to access sensitive user data in order to perform useful tasks and the need to protect that data from unauthorized access, misuse, or exposure. Existing cloud-based solutions require users to sacrifice privacy in exchange for functionality, creating a trade-off that many users and organizations find unacceptable, particularly in privacy-sensitive domains such as healthcare, finance, legal services, and government operations.')
body('The system must therefore be designed to interpret natural language instructions from the user, convert them into structured actions using well-defined schemas, and execute them directly within the user\u2019s local environment without transmitting any data to external servers. The system must operate entirely on local hardware to eliminate reliance on cloud infrastructure, ensuring data sovereignty and reducing latency. Additionally, it should provide a secure execution mechanism that validates all actions before execution, prevents unintended or harmful operations, and supports scalable integration with various tools and applications through a modular plugin architecture.')

h2("1.5 Relevance of the Project")
body('The proposed system is highly relevant in the current technological landscape, where several converging trends are driving demand for the type of solution that Dione provides. The growing shift towards Agentic AI represents a fundamental evolution in how AI systems are designed and deployed. Unlike traditional chatbot-style AI that simply responds to queries, agentic AI systems are designed to take autonomous actions on behalf of the user, effectively serving as digital agents that can independently plan, execute, and monitor complex tasks. Industry analysts predict that agentic AI will be one of the most transformative technology trends of the next decade, with applications spanning personal productivity, enterprise automation, scientific research, and creative work.')
body('The rise of Edge Computing and on-device AI processing is another trend that directly supports the relevance of Dione\u2019s local-first approach. Advances in hardware capabilities, including the development of powerful mobile processors, dedicated AI accelerators such as NVIDIA\u2019s RTX series GPUs and Apple\u2019s Neural Engine, and the optimization of model architectures through techniques like quantization and pruning, have made it increasingly feasible to run sophisticated AI models directly on consumer devices. This trend toward edge AI reduces reliance on cloud infrastructure, improves response times, and enhances data privacy.')
body('Dione addresses these trends by enabling autonomous task execution without exposing sensitive data to external entities. It is particularly relevant for applications in domains such as personal productivity, where users need AI assistance with daily tasks like email management, scheduling, and document organization; enterprise automation, where businesses need to automate repetitive workflows while maintaining control over proprietary data; and privacy-sensitive sectors including finance, healthcare, and legal services, where regulatory requirements mandate strict data handling practices. The project aligns with the future direction of AI systems that prioritize decentralization, security, and user ownership, making it a timely and significant contribution to the field.')

h2("1.6 Methodology Used")
body('The development of Dione follows a modular and structured approach based on a micro-kernel architecture, which separates the core orchestration logic from the various functional modules that handle specific aspects of the system\u2019s operation. This architectural choice ensures flexibility, scalability, and ease of maintenance, as individual modules can be developed, tested, and updated independently without affecting the rest of the system.')
body('The system separates the reasoning and execution components into distinct layers. The reasoning layer is responsible for understanding user intent, generating action plans, and making decisions about which tools to use and in what order. The execution layer is responsible for translating these plans into concrete actions, invoking the appropriate plugins, and handling the results. This separation of concerns allows each layer to be optimized independently and enables the system to support multiple LLM backends and execution environments.')
body('A ReAct (Reason + Act) loop is implemented as the core operational paradigm, allowing the system to iteratively reason about a task, perform an action, observe the result, and refine its approach based on the outcome. This iterative approach is particularly well-suited for complex, multi-step tasks where the optimal course of action may not be known in advance and must be discovered through trial and refinement. The ReAct loop draws inspiration from the seminal work by Yao et al. (2023), which demonstrated that combining reasoning and acting in a single loop significantly improves the performance of language model agents on complex tasks.')
body('The system integrates local LLMs through frameworks such as Ollama and Llama.cpp, enabling on-device inference without any network dependency. Context management is achieved using Retrieval-Augmented Generation (RAG) techniques with a vector database powered by ChromaDB to maintain conversational memory, store user preferences, and improve response accuracy over time. Task execution is handled through a plugin-based architecture, where each tool \u2013 such as the Gmail plugin, WhatsApp plugin, file system plugin, and calendar plugin \u2013 operates as an independent module with a well-defined interface and sandboxed execution environment.')
body('To ensure system reliability and security, validation mechanisms using libraries such as Pydantic are incorporated to verify the structure and content of all generated commands before execution. Permission-based execution controls ensure that sensitive operations require explicit user approval, while sandboxing techniques isolate plugin execution from the core system to prevent malicious or erroneous actions from causing system-wide damage. This comprehensive methodology ensures that the system remains robust, secure, and efficient while performing complex multi-step operations in a privacy-preserving manner.')
pb()

# ============ SAVE MARKER (for combiner) ============
# Save intermediate state
print("Part 1 complete: Front matter + Chapter 1 saved.")
