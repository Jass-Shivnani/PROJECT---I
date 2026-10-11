"""Part 4: Chapters 5-8, References, Appendix (Expanded) + SAVE"""

# ============ CHAPTER 5 ============
h1("Chapter 5: Implementation Results and Discussions")
body('This chapter presents a comprehensive account of the implementation details, experimental setup, and evaluation of the proposed system, Dione. Since the system focuses on agentic AI and autonomous task execution rather than traditional dataset-based machine learning, the discussion emphasizes system inputs, context handling, execution workflows, performance analysis, and a comparative gap analysis with existing systems. The chapter documents the data acquisition strategy, preprocessing techniques, experimental configuration, evaluation metrics, and the results of the gap analysis, providing a thorough assessment of the system\'s capabilities and its advantages over existing solutions.')

h2("5.1 Data Collection / Acquisition")
body('Unlike traditional machine learning systems that rely on static, pre-collected datasets for training and evaluation, Dione operates on dynamic, real-time data sources that are generated and consumed during the course of normal system operation. This fundamental difference in data handling reflects the system\'s nature as an interactive agent rather than a batch-processing model. The data acquisition strategy is designed to support the system\'s ability to understand user intent, maintain contextual awareness, and execute actions across diverse application domains.')
body('The primary source of data is user input, consisting of natural language commands and instructions entered through the CLI or web interface. These inputs range from simple, single-action commands such as "create a folder on the desktop" to complex, multi-step instructions such as "read my latest email, summarize it, and send a response." The diversity and unpredictability of user inputs represent a key challenge for the system, as it must be capable of understanding and acting on a virtually unlimited range of natural language expressions.')
body('System context constitutes the second major data source, encompassing information about the current state of the user\'s computing environment. This includes the active window and application, the current working directory, recent file system changes, running processes, and system resource utilization. The system context provides crucial information that helps the LLM make informed decisions about how to execute requested tasks. For example, if a user asks to "save this file," the system context reveals which application and file are currently active, enabling the system to determine the appropriate save operation.')
body('Local storage represents a rich repository of user data that the system can access and process in response to user requests. This includes documents in various formats such as PDF, DOCX, and TXT files, as well as images, spreadsheets, and other file types stored on the local file system. The system indexes and embedds relevant documents using the ChromaDB vector database, enabling efficient semantic search and retrieval when contextual information is needed.')
body('External APIs provide access to cloud-based services such as Gmail for email operations, Google Calendar for scheduling, and messaging platforms such as WhatsApp for communication tasks. While these services require internet connectivity, all API communication is initiated and managed locally by Dione\'s plugins, ensuring that the user\'s credentials and data are handled entirely on the local device. The system uses OAuth 2.0 authentication flows that store tokens locally, never transmitting credentials to any third-party server other than the service provider itself.')
body('The vector database powered by ChromaDB serves as both a data source and a data store, containing embeddings of past interactions, document summaries, and contextual information that has been accumulated over the course of the system\'s operation. This database enables the RAG-based context retrieval system that enriches user inputs with relevant historical information, improving the accuracy and relevance of the system\'s responses over time. Data is acquired dynamically at runtime, making the system adaptive and context-aware, eliminating the need for predefined datasets and allowing real-time decision-making based on the most current information available.')

h2("5.2 Data Preprocessing Techniques")
body('Since the primary input to the Dione system is unstructured natural language text, preprocessing is essential for transforming raw user input into a format that enables accurate reasoning by the LLM and reliable execution by the plugin system. The preprocessing pipeline consists of multiple stages, each addressing a specific aspect of input transformation.')
body('Text Normalization is the first preprocessing step, responsible for cleaning and standardizing raw user input. This includes correcting common spelling errors, expanding abbreviations and contractions, resolving ambiguous references using contextual clues, and normalizing whitespace and punctuation. The normalization process ensures that the LLM receives clean, consistent input regardless of variations in the user\'s typing style or language use. For example, inputs like "pls send msg to john abt meeting tmrw" are normalized to a more standard form before being processed by the LLM.')
body('Tokenization converts the normalized input text into a sequence of tokens that can be processed by the LLM. The tokenization scheme must match the specific model being used, as different models employ different tokenization strategies such as Byte Pair Encoding (BPE), WordPiece, or SentencePiece. The system\'s Model Adapter module handles tokenization transparently, applying the correct tokenization scheme based on the active model configuration.')
body('Context Augmentation through RAG is a critical preprocessing step that retrieves relevant information from the vector database and appends it to the user\'s input before sending it to the LLM. The retrieval process uses semantic similarity search to identify past interactions, stored documents, and system state information that are relevant to the current request. The retrieved context is formatted into a structured prompt template that clearly delineates the user\'s current input from the supplementary context, enabling the LLM to leverage the additional information without confusing it with the current request.')
body('Schema Structuring converts the LLM\'s natural language outputs into structured JSON format that can be parsed and executed by the plugin system. The system uses carefully designed output format instructions in the LLM prompt to encourage the generation of well-formed JSON objects that specify the target plugin, function name, and parameters for each action. Post-processing logic handles cases where the LLM\'s output deviates from the expected format, applying pattern matching and correction heuristics to extract actionable commands from imperfect outputs.')
body('Validation Preprocessing using Pydantic models provides the final preprocessing step before command execution. Each generated command is validated against a Pydantic schema that defines the expected structure, data types, and constraints for the command\'s parameters. This validation catches malformed commands, missing required parameters, out-of-range values, and type mismatches before they can cause errors during execution. Commands that fail validation are rejected with detailed error messages that are fed back to the LLM, prompting it to generate a corrected version. These preprocessing steps collectively ensure that user input is transformed into a format that is suitable for both reasoning and execution, significantly reducing errors and improving the overall reliability of the system.')

h2("5.3 Experimental Setup")
body('The system was tested in a controlled local environment designed to simulate realistic usage conditions while providing consistent and reproducible results. The experimental setup was configured to evaluate the system\'s performance across multiple dimensions, including task completion accuracy, response latency, privacy compliance, and safety enforcement.')
body('The hardware configuration used for testing includes an Intel Core i5 12th Generation processor providing adequate CPU performance for system operations and model inference, 16 GB of DDR4 system RAM for general system operations with an additional 32 GB configuration tested for large model scenarios, an NVIDIA RTX 3060 GPU with 12 GB of VRAM for accelerated model inference using CUDA, and a 512 GB NVMe SSD providing fast storage for model files, vector database, and system data. An alternative Apple Silicon M2 configuration was also tested to verify cross-platform compatibility.')
body('The software configuration includes Python 3.12 as the runtime environment, Ollama version 0.2 serving Mistral 7B and LLaMA 2 7B models for local inference, ChromaDB version 0.4 for vector storage and retrieval, SQLite 3 for structured data logging and configuration, Pydantic version 2 for schema validation, and FastAPI for the backend API server that handles communication between the CLI client and the orchestration engine.')
body('The test scenarios were designed to cover a representative range of real-world use cases at varying levels of complexity. Single-step tasks include operations such as creating a file at a specified location with specified content, reading the contents of a specific file, and listing files in a directory. These tasks test the basic input-output pipeline and validate that individual plugins function correctly. Multi-step tasks include complex workflows such as retrieving a document from the file system, summarizing its contents using the LLM, and sending the summary via email. These tasks test the ReAct loop\'s ability to coordinate multiple sequential operations and handle intermediate results. Context-based tasks test the system\'s ability to use information from previous interactions to complete current requests, such as referencing a previously discussed file or recalling a user preference. These tasks validate the effectiveness of the RAG-based context retrieval system.')

ip("Figure 5.1 \u2013 CLI Screenshot: File Creation Task")
ip("Figure 5.2 \u2013 File Explorer Validation of Created File")
ip("Figure 5.3 \u2013 CLI Screenshot: WhatsApp Message Sending Task")
ip("Figure 5.4 \u2013 WhatsApp Mobile Validation Screenshot")
ip("Figure 5.5 \u2013 CLI Screenshot: Gmail Read and Send Task")
ip("Figure 5.6 \u2013 Gmail Web Interface Validation Screenshot")

h2("5.4 Evaluation Metrics")
body('The evaluation of Dione\'s performance uses a set of metrics specifically designed for agentic AI systems, focusing on the practical utility of the system rather than traditional machine learning metrics such as accuracy on benchmark datasets. These metrics were selected to assess the system\'s effectiveness across the key dimensions of task completion, responsiveness, efficiency, privacy, and safety.')
body('The Task Success Rate (TSR) measures the percentage of user-initiated tasks that are successfully completed to the user\'s satisfaction. A task is considered successful if all required actions are executed correctly, the expected outputs are produced, and no unintended side effects occur. The TSR is calculated as the ratio of successfully completed tasks to total attempted tasks, expressed as a percentage. This metric provides a comprehensive measure of the system\'s end-to-end effectiveness, capturing failures at any stage of the pipeline including intent misunderstanding, incorrect action generation, validation failures, and execution errors.')
body('Time-to-Action (TTA) measures the elapsed time from when the user submits an input to when the system begins executing the first action. This metric reflects the system\'s responsiveness and is critical for user satisfaction, as long delays between input and action create a perception of sluggishness. The TTA is influenced by factors including model inference speed, context retrieval latency, and validation processing time. The target TTA for simple single-step tasks is less than three seconds.')
body('Token Generation Speed measures the rate at which the LLM generates output tokens, expressed in tokens per second. This metric directly reflects the inference performance of the local model and is heavily dependent on the hardware configuration, model size, and quantization level. Higher token generation speeds translate to faster response times and a more fluid user experience. The target for the system is a minimum of 10 tokens per second on the recommended hardware configuration.')
body('The Privacy Metric quantifies the system\'s compliance with its privacy-first design principles by measuring the volume of data transmitted to external servers during operation. The target for this metric is zero unauthorized data leakage, meaning that no user data should be sent to any server other than the specific service endpoints required for task execution (such as Gmail\'s SMTP server for sending emails). The metric is verified through network traffic monitoring during test sessions.')
body('The Safety Metric tracks the system\'s ability to prevent the execution of potentially unsafe or unauthorized commands. This includes commands that could delete important files, modify system configurations, send messages without authorization, or perform any other action that could have negative consequences. The target is one hundred percent prevention of unsafe commands that are not explicitly approved by the user through the confirmation mechanism.')

h2("5.5 Gap Analysis of Existing Systems")
body('A comprehensive comparative analysis was performed between Dione and existing cloud-based AI assistant systems to identify the specific gaps that Dione addresses and to quantify its advantages over current solutions.')
tbl(["Feature","Existing Systems (Cloud-based)","Dione (Proposed System)"],[
    ("Execution Capability","Limited to predefined commands","Full autonomous task execution via plugins"),
    ("Privacy","Low \u2013 data transmitted to cloud servers","High \u2013 all processing occurs locally on device"),
    ("Security","Vulnerable to breaches and data leaks","Controlled execution with validation and sandboxing"),
    ("Latency","High \u2013 dependent on network round-trip time","Low \u2013 local inference with no network dependency"),
    ("Autonomy","Partial \u2013 single-step operations only","High \u2013 multi-step workflows via ReAct loop"),
    ("Scalability","Limited by API rate limits and costs","Modular plugin-based architecture, no API costs"),
    ("Offline Operation","Not possible without internet","Fully functional for local tasks"),
    ("Data Sovereignty","Data stored on third-party servers","Complete user control over all data"),
    ("Customization","Limited by vendor policies","Fully customizable through plugins and model selection"),
])
body('Table 5.1 \u2013 Comprehensive Gap Analysis: Dione vs. Existing Cloud-Based Systems')
body('The gap analysis reveals that Dione addresses several fundamental limitations of existing cloud-based AI systems. The most significant advantages are in the areas of privacy and data sovereignty, where Dione\'s local-first architecture provides absolute protection against unauthorized data exposure. The autonomous multi-step execution capability, powered by the ReAct loop, enables Dione to handle complex workflows that are beyond the capabilities of existing systems. The elimination of network dependency and API costs makes Dione more accessible and reliable than cloud-based alternatives. These advantages collectively position Dione as a next-generation AI assistant that advances the state of the art in agentic AI while maintaining the highest standards of privacy and security.')
pb()

# ============ CHAPTER 6 ============
h1("Chapter 6: Plan of Action for the Next Semester")
body('This chapter outlines the progress achieved during the current semester as part of Capstone Project I, and presents a detailed plan for the upcoming semester under Capstone Project II. The focus of the next phase is on transitioning from the current state of design and partial implementation to a fully functional, optimized, and deployable system that demonstrates all of the capabilities described in this report.')

h2("6.1 Work Done Till Date")
body('Significant progress has been achieved during the current semester across multiple dimensions of the project. In the area of Problem Identification and Research, the team conducted an extensive analysis of the current AI landscape, identifying the Actuation Gap as the central problem to be addressed. The limitations of existing cloud-based agentic AI systems were thoroughly documented, and the case for a local-first, privacy-preserving approach was established through a combination of literature review and expert consultation.')
body('The Literature Survey phase involved a comprehensive review of over twenty academic papers, industry reports, and technical resources spanning the fields of large language models, agentic AI, retrieval-augmented generation, and privacy-preserving computing. Key papers including Toolformer, ReAct, Generative Agents, and RAG were analyzed in depth, and their contributions and limitations were mapped to the design requirements of Dione. A thorough patent search confirmed the novelty of the proposed approach.')
body('During the System Design phase, the complete architecture of Dione was designed following a micro-kernel philosophy with clear separation of concerns. Block diagrams and modular diagrams were prepared, the ReAct-based workflow was defined, and detailed design models including DFDs, use case diagrams, flowcharts, activity diagrams, state transition diagrams, and ER diagrams were created. The plugin interface specification was designed to support modular extensibility.')
body('Requirement Analysis activities included the identification and documentation of comprehensive functional and non-functional requirements, the establishment of system constraints and hardware/software specifications, and the mapping of project objectives to UN Sustainable Development Goals.')
body('In Initial Implementation, the local LLM environment was successfully set up using Ollama with support for Mistral 7B and LLaMA 2 models. A basic input-processing pipeline was implemented, demonstrating the feasibility of local inference for agentic tasks. The initial plugin structure was developed, with working prototypes of the file system plugin, Gmail plugin, and WhatsApp plugin. The ReAct loop was implemented in its basic form, successfully coordinating multi-step task execution across plugins.')
body('Documentation activities throughout the semester included the preparation of the project synopsis, the progressive development of this comprehensive project report, and the creation of presentation materials for project reviews.')

h2("6.2 Plan of Action for Project II")
body('The upcoming semester will focus on completing the full system development, conducting rigorous optimization and testing, and preparing the system for final demonstration and evaluation. The planned activities are organized into seven key areas.')

h3("6.2.1 Core System Development")
body('The orchestration engine will be completed with full implementation of the ReAct loop, including advanced features such as multi-turn reasoning, error recovery, and dynamic strategy adjustment. The reasoning-to-action conversion pipeline will be improved to handle a wider range of natural language input patterns and generate more accurate and reliable action specifications. Integration between the LLM and plugins will be enhanced through refined prompt templates, improved output parsing, and better error handling mechanisms.')

h3("6.2.2 Plugin Expansion")
body('The plugin ecosystem will be significantly expanded to cover a broader range of use cases. New plugins will include email automation with advanced capabilities such as inbox search, thread management, and attachment handling; calendar scheduling with support for event creation, modification, conflict detection, and reminder management; enhanced file system management with support for file search, batch operations, and content analysis; web browsing capabilities for information retrieval and web-based task automation; and API integrations with popular productivity tools and services. The plugin interface will be standardized and documented to enable third-party plugin development.')

h3("6.2.3 Security and Validation Enhancement")
body('The safety guardrail system will be strengthened with additional validation rules, improved threat detection capabilities, and more granular permission controls. A comprehensive permission-based execution system will be implemented, allowing users to configure detailed access policies for each plugin and operation type. A confirmation layer for high-risk actions will be refined with contextual explanations that help users understand the implications of approving or denying each operation.')

h3("6.2.4 Performance Optimization")
body('Model inference performance will be optimized through the use of advanced quantization techniques, inference caching, and hardware-specific optimizations. Latency in context retrieval will be reduced through improved indexing strategies and query optimization in ChromaDB. Memory management will be improved to support longer conversation sessions and larger context windows without degrading system performance.')

h3("6.2.5 User Interface Development")
body('A web-based graphical user interface will be developed using modern frontend technologies, providing an intuitive and visually appealing interaction experience. The GUI will include features such as conversation history display, task progress visualization, plugin management controls, and system configuration options. Usability testing will be conducted to identify and address interaction design issues.')

h3("6.2.6 Testing and Evaluation")
body('A comprehensive testing framework will be developed, including benchmark tasks inspired by the AgentBench evaluation suite. Testing will cover all evaluation metrics defined in this report, including Task Success Rate, Time-to-Action, Token Generation Speed, Privacy Metric, and Safety Metric. Error analysis will be performed to identify common failure patterns and guide targeted improvements.')

h3("6.2.7 Final Integration and Deployment")
body('All modules will be integrated into a complete, production-ready system. System-level testing will be performed to verify end-to-end functionality, performance under load, and robustness against edge cases. The system will be prepared for final demonstration, including the creation of demo scripts, presentation materials, and a user guide.')
pb()

# ============ CHAPTER 7 ============
h1("Chapter 7: Conclusion")
body('The development of Dione \u2013 a Local Large Action Model (LAM) Orchestration Engine \u2013 represents a significant advancement in the evolution of artificial intelligence systems, particularly in addressing the long-standing limitation known as the Actuation Gap. While modern Large Language Models have demonstrated remarkable capabilities in reasoning, natural language understanding, and content generation, they remain fundamentally constrained by their inability to execute real-world actions. This project bridges that gap by introducing an intelligent orchestration layer that enables seamless interaction between AI reasoning and system-level execution, all within the privacy-preserving confines of the user\'s local device.')
body('The core contribution of this project lies in its local-first architecture, which fundamentally redefines how agentic AI systems are designed and deployed. Unlike conventional cloud-based approaches that require users to expose sensitive data to external servers for processing, Dione ensures that all reasoning, context handling, and decision-making occur entirely on the user\'s device. This architectural choice guarantees data sovereignty, enhanced privacy, and reduced security risks, making the system particularly suitable for applications involving confidential or sensitive information in domains such as healthcare, finance, legal services, and personal productivity. By eliminating dependency on remote servers, the system also improves reliability by functioning without internet connectivity for local tasks, and reduces latency by avoiding network round-trip times, thereby enhancing the overall user experience.')
body('From a technical perspective, the system integrates several advanced concepts into a cohesive and functional architecture. The ReAct (Reason + Act) loop serves as the core operational paradigm, enabling iterative reasoning and action execution that allows the system to tackle complex, multi-step workflows dynamically. The Retrieval-Augmented Generation (RAG) system, powered by ChromaDB, provides contextual memory that improves the accuracy and relevance of the system\'s responses over time. The modular plugin-based execution framework ensures scalability and extensibility, allowing new functionalities to be added through plugins without modifying the core system. The Safety Guardrail module provides multi-layered security controls that validate all actions before execution, ensuring that the system operates safely and in accordance with user-defined policies.')
body('The project has successfully demonstrated the feasibility and effectiveness of the proposed approach through working implementations of several key plugins, including file system operations, email management through Gmail, and messaging through WhatsApp. These demonstrations validate that it is possible to build a fully functional agentic AI system that operates locally, handles real-world tasks autonomously, and maintains the highest standards of privacy and security. The gap analysis presented in this report confirms that Dione addresses multiple fundamental limitations of existing cloud-based AI systems, positioning it as a significant contribution to the field of agentic AI.')
body('Looking forward, the project has laid a strong foundation for the next phase of development, which will focus on expanding the plugin ecosystem, optimizing performance, enhancing security mechanisms, and developing a user-friendly graphical interface. The completion of these planned activities will result in a comprehensive, production-ready system that demonstrates the full potential of local, privacy-preserving agentic AI. Dione represents not just a technical achievement, but a step toward a future where AI systems empower users with intelligent automation while respecting their fundamental right to privacy and control over their personal data.')
pb()

# ============ CHAPTER 8: REFERENCES ============
h1("Chapter 8: References")
refs = [
    '[1] Schick, T., Dwivedi-Yu, J., Dessi, R., Raileanu, R., Lomeli, M., Zettlemoyer, L., Cancedda, N., and Scialom, T. (2023). "Toolformer: Language Models Can Teach Themselves to Use Tools." arXiv preprint arXiv:2302.04761.',
    '[2] Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., and Zhou, D. (2022). "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." Advances in Neural Information Processing Systems, 35.',
    '[3] Nakajima, Y. (2023). "BabyAGI: Task-driven Autonomous Agent." GitHub Repository. Available: https://github.com/yoheinakajima/babyagi.',
    '[4] OpenAI. (2023). "GPT-4 Technical Report." arXiv preprint arXiv:2303.08774.',
    '[5] Chase, H. (2022). "LangChain: Building Applications with LLMs through Composability." Available: https://github.com/langchain-ai/langchain.',
    '[6] Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., and Cao, Y. (2023). "ReAct: Synergizing Reasoning and Acting in Language Models." arXiv preprint arXiv:2210.03629.',
    '[7] Touvron, H., Martin, L., Stone, K., et al. (2023). "Llama 2: Open Foundation and Fine-Tuned Chat Models." Meta AI. arXiv preprint arXiv:2307.09288.',
    '[8] Jiang, A. Q., Sablayrolles, A., Mensch, A., et al. (2023). "Mistral 7B." arXiv preprint arXiv:2310.06825.',
    '[9] Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Kuttler, H., Lewis, M., Yih, W., Rocktaschel, T., Riedel, S., and Kiela, D. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." Advances in Neural Information Processing Systems, 33.',
    '[10] Dettmers, T., Pagnoni, A., Holtzman, A., and Zettlemoyer, L. (2023). "QLoRA: Efficient Finetuning of Quantized Large Language Models." arXiv preprint arXiv:2305.14314.',
    '[11] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., and Polosukhin, I. (2017). "Attention Is All You Need." Advances in Neural Information Processing Systems, 30.',
    '[12] Park, J. S., O\'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., and Bernstein, M. S. (2023). "Generative Agents: Interactive Simulacra of Human Behavior." arXiv preprint arXiv:2304.03442.',
    '[13] Mialon, G., Dessi, R., Lomeli, M., Nalmpantis, C., Pasunuru, R., Raileanu, R., Roziere, B., Schick, T., Dwivedi-Yu, J., Celikyilmaz, A., Grave, E., LeCun, Y., and Scialom, T. (2023). "Augmented Language Models: A Survey." arXiv preprint arXiv:2302.07842.',
    '[14] Significant-Gravitas. (2023). "AutoGPT: An Autonomous GPT-4 Experiment." GitHub Repository. Available: https://github.com/Significant-Gravitas/AutoGPT.',
    '[15] Kandpal, N., Deng, H., Roberts, A., Wallace, E., and Raffel, C. (2023). "Large Language Models Struggle to Learn Long-Tail Knowledge." arXiv preprint arXiv:2211.08411.',
]
for ref in refs: body(ref)
pb()

# ============ APPENDIX ============
h1("Appendix")
h2("A. List of Figures")
tbl(["Figure No.","Heading","Page No."],[
    ("4.1","Block Diagram of the Dione System",""),
    ("4.2","Modular Diagram of the Dione System",""),
    ("4.3","Use Case Diagram",""),
    ("4.4","Data Flow Diagram (Level 0)",""),
    ("4.5","Data Flow Diagram (Level 1)",""),
    ("4.6","System Flowchart (ReAct Loop)",""),
    ("4.7","CLI Interface: File Creation Task",""),
    ("4.8","File Explorer Validation",""),
    ("4.9","CLI Interface: WhatsApp Message Task",""),
    ("4.10","WhatsApp Mobile Validation",""),
    ("4.11","CLI Interface: Gmail Read/Send Task",""),
    ("4.12","Gmail Web Validation",""),
    ("4.13","Gantt Chart Representation",""),
])
doc.add_paragraph()
h2("B. List of Tables")
tbl(["Table No.","Heading","Page No."],[
    ("CO","Course Outcomes for Capstone Project",""),
    ("4.1","Project Schedule and Timeline",""),
    ("5.1","Gap Analysis: Dione vs. Existing Systems",""),
])
doc.add_paragraph()
h2("C. Paper Publications")
body("[Acceptance mail, Published paper, Plagiarism report, and Certificate of publication/presentation \u2013 To be attached in the final submission.]")
doc.add_paragraph()
h2("D. Project Review Sheets")
body("[Progress Review Sheet 1 and 2 \u2013 To be attached in the final submission.]")

# ============ SAVE FINAL DOCX ============
output_path = 'docs/Dione_Report_v2.docx'
doc.save(output_path)
print(f"Final report saved to: {output_path}")
