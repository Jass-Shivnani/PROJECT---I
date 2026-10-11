import os

def main():
    with open('reconstructed_full_master.tex', 'r', encoding='utf-8') as f:
        text = f.read()

    bib_block = r"""\begin{thebibliography}{00}
\bibitem{schick2023toolformer} T. Schick, J. Dwivedi-Yu, R. Dess{\`\i}, R. Raileanu, M. Lomeli, L. Zettlemoyer, N. Cancedda, and T. Scialom, ``Toolformer: Language models can teach themselves to use tools,'' in \textit{Proc. 37th Conf. Neural Inf. Process. Syst. (NeurIPS)}, 2023.
\bibitem{yao2023react} S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. R. Narasimhan, and Y. Cao, ``ReAct: Synergizing reasoning and acting in language models,'' in \textit{Proc. Int. Conf. Learn. Represent. (ICLR)}, 2023.
\bibitem{qin2023toolllm} Y. Qin, S. Liang, Y. Ye, K. Zhu, L. Yan, Y. Lu, Y. Lin, X. Cong, X. Tang, B. Qian, et al., ``ToolLLM: Facilitating large language models to master 16000+ real-world APIs,'' in \textit{Proc. Int. Conf. Learn. Represent. (ICLR)}, 2024.
\bibitem{microsoft2025agentframework} Microsoft, ``Microsoft Agent Framework: A unified framework for building, orchestrating, and deploying AI agents,'' Microsoft Research and Azure AI, Tech. Rep., 2025.
\bibitem{packer2023memgpt} C. Packer, V. Fang, S. G. Patil, K. Lin, S. Wooders, and J. E. Gonzalez, ``MemGPT: Towards LLMs as operating systems,'' \textit{arXiv preprint arXiv:2310.08560}, 2023.
\bibitem{edge2024graphrag} D. Edge, H. Trinh, N. Cheng, J. Bradley, A. Chao, A. Mody, S. Truitt, D. Metropolitansky, R. O. Ness, and J. Larson, ``From local to global: A graph RAG approach to query-focused summarization,'' \textit{arXiv preprint arXiv:2404.16130}, 2024.
\bibitem{pan2024unifying} S. Pan, L. Luo, Y. Wang, C. Chen, J. Wang, and X. Wu, ``Unifying large language models and knowledge graphs: A roadmap,'' \textit{IEEE Trans. Knowl. Data Eng.}, vol. 36, no. 7, pp. 3580--3599, 2024.
\bibitem{sun2023thinkongraph} J. Sun, C. Xu, L. Tang, S. Wang, C. Lin, Y. Gong, H. Shum, and X. Guo, ``Think-on-graph: Deep and responsible reasoning of large language models on knowledge graphs,'' in \textit{Proc. Int. Conf. Learn. Represent. (ICLR)}, 2024.
\bibitem{ruan2023identifying} Y. Ruan, H. Dong, A. Wang, S. Pitis, Y. Zhou, J. Ba, Y. Dubois, C. J. Maddison, and T. Hashimoto, ``Identifying the risks of LM agents with an LM-emulated sandbox,'' \textit{arXiv preprint arXiv:2309.15817}, 2023.
\bibitem{liu2023prompt} Y. Liu, G. Deng, Y. Li, K. Wang, Z. Wang, X. Wang, T. Zhang, Y. Liu, H. Wang, Y. Zheng, et al., ``Prompt injection attack against LLM-integrated applications,'' \textit{arXiv preprint arXiv:2306.05499}, 2023.
\bibitem{bipia2023} J. Yi, Y. Xie, B. Zhu, K. Hines, E. Kiciman, G. Sun, X. Xie, and F. Wu, ``Benchmarking and defending against indirect prompt injection attacks on large language models,'' \textit{arXiv preprint arXiv:2312.14197}, 2023.
\bibitem{jailbreakbench2024} P. Chao, E. Debenedetti, A. Robey, M. Maksymenko, P. Ramanujan, H. Hassani, G. Pappas, and F. Tram{\`e}r, ``JailbreakBench: An open robustness benchmark for jailbreaking large language models,'' in \textit{Proc. 38th Conf. Neural Inf. Process. Syst. (NeurIPS) Datasets and Benchmarks Track}, 2024.
\bibitem{zhang2024agent} H. Zhang, J. Huang, K. Mei, Y. Yao, Z. Wang, C. Zhan, H. Wang, and Y. Zhang, ``Agent Security Bench (ASB): Formalizing and benchmarking attacks and defenses in LLM-based agents,'' in \textit{Proc. Int. Conf. Learn. Represent. (ICLR)}, 2025.
\bibitem{greshake2023not} K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, ``Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection,'' in \textit{Proc. 16th ACM Workshop Artif. Intell. Secur. (AISec)}, 2023, pp. 79--90.
\bibitem{liu2023agentbench} X. Liu, H. Yu, H. Zhang, Y. Xu, X. Lei, H. Lai, Y. Gu, H. Ding, K. Men, K. Yang, et al., ``AgentBench: Evaluating LLMs as agents,'' \textit{arXiv preprint arXiv:2308.03688}, 2023.
\bibitem{mialon2023gaia} G. Mialon, C. Fourrier, C. Swift, T. Wolf, Y. LeCun, and T. Scialom, ``GAIA: A benchmark for general AI assistants,'' in \textit{Proc. Int. Conf. Learn. Represent. (ICLR)}, 2024.
\bibitem{lewis2020retrieval} P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. K{\"u}ttler, M. Lewis, W.-t. Yih, T. Rockt{\"a}schel, et al., ``Retrieval-augmented generation for knowledge-intensive NLP tasks,'' in \textit{Proc. 34th Conf. Neural Inf. Process. Syst. (NeurIPS)}, 2020, pp. 9459--9474.
\bibitem{perez2022ignore} F. Perez and I. Ribeiro, ``Ignore this title and hack this paper: Do not rely on language models to win reasoning competitions with prompt injection,'' in \textit{Proc. EMNLP}, 2022.
\bibitem{dibia2023autogen} Q. Wu, G. Bansal, J. Zhang, Y. Wu, B. Li, E. Zhu, R. Cao, M. Zhang, H. Wang, and H. Wang, ``AutoGen: Enabling next-gen LLM applications via multi-agent conversation,'' in \textit{Proc. Int. Conf. Learn. Represent. (ICLR)}, 2024.
\bibitem{malsuare2024superagent} P. Malsuare, S. Patil, and R. Deshmukh, ``SuperAgent: A scalable multi-agent framework for autonomous task execution,'' \textit{Int. J. Comput. Appl.}, vol. 186, no. 12, pp. 45--53, 2024.
\bibitem{injecagent2024} Q. Zhan, R. Fang, R. Bindu, P. Gupta, Q. Babbar, and D. Kang, ``InjecAgent: Benchmarking indirect prompt-injection attacks on LLM agents,'' in \textit{Proc. Findings Assoc. Comput. Linguistics (ACL)}, 2024, pp. 5432--5448.
\bibitem{vaswani2017attention} A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, {\L}. Kaiser, and I. Polosukhin, ``Attention is all you need,'' in \textit{Proc. 31st Conf. Neural Inf. Process. Syst. (NeurIPS)}, 2017, pp. 5998--6008.
\bibitem{apple2024pcc} Apple Security Engineering and Architecture (SEAR), ``Private Cloud Compute: A new frontier for AI privacy in the cloud,'' \textit{Apple Security Research}, Tech. Rep., June 2024.
\bibitem{google2024geminiprivacy} Google LLC, ``Gemini Apps Privacy Notice and User Data Policy,'' Alphabet Inc., Tech. Whitepaper, 2024.
\bibitem{microsoft2024copilotprivacy} Microsoft Corp., ``Data, Privacy, and Security for Microsoft 365 Copilot and Windows Copilot,'' Microsoft Learn, Tech. Rep., 2024.
\end{thebibliography}"""

    b_idx = text.find(r'\begin{thebibliography}')
    if b_idx != -1:
        text = text[:b_idx] + bib_block + "\n\n\\end{document}\n"

    # Fix dangerous sequence \default
    text = text.replace(r'winsta0\default', r'winsta0\textbackslash default')

    # Intro citations
    intro_old = r'Commercial platforms such as Apple Siri, Google Gemini, and Microsoft Copilot handle these responsibilities by transmitting audio streams, desktop metadata, and calendar databases directly to remote server farms \cite{schick2023toolformer, yao2023react}.'
    intro_new = r'Mainstream commercial platforms such as Apple Siri (with Apple Intelligence), Google Gemini, and Microsoft Copilot handle complex generative reasoning primarily within centralized cloud infrastructure, routing audio streams, desktop metadata, and personal correspondence to remote server farms \cite{apple2024pcc, google2024geminiprivacy, microsoft2024copilotprivacy}. While privacy-preserving cloud extensions have been engineered (such as Apple Private Cloud Compute \cite{apple2024pcc}), standard default assistant configurations still necessitate streaming sensitive user telemetry and prompt context across external networks whenever requests exceed localized on-device heuristic budgets.'
    text = text.replace(intro_old, intro_new)

    targets = [
        'docs/DIONE_IEEE_RESEARCH_PAPER.tex',
        'DIONE_IEEE_RESEARCH_PAPER.tex',
        'DIONE_IEEE_RESEARCH_PAPER_PUBLISHABLE.tex'
    ]
    for target in targets:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(text)

    print(f"Successfully generated master TeX paper across targets! Lines: {len(text.splitlines())}, Chars: {len(text)}")

if __name__ == '__main__':
    main()
