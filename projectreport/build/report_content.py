"""Content of the SecuLayer project report: front matter, references, and the chapters
(content_ch1_3.py, content_ch4_5.py, content_ch6_8.py). Every measured number traces to
PROGRESS.md at commit b92144d (M5) or to the files in projectreport/build/data/, which the scripts in
this directory produced from the recordings committed by then.
"""
from content_ch1_3 import CH1, CH2, CH3
from content_ch4_5 import CH4, CH5
from content_ch6_8 import APPENDICES, CH6, CH7, CH8, REFERENCES_BLOCK

TITLE = "SecuLayer: A Layered Defense Against Prompt Injection in LLM-Integrated Applications"
RUNNING_HEADER = "SecuLayer: A Layered Defense Against Prompt Injection"

# Everything the author must fill in. Each appears in the document exactly as written here.
PH = {
    "branch": "[NAME OF BRANCH]",
    "roll": "[ROLL NO.]",
    "exam": "[UNIVERSITY EXAM NO.]",
    "guide": "[NAME OF GUIDE]",
    "date": "[DATE]",
    "signature": "[SIGNATURE]",
}
STUDENTS = [("Akash Chaudhari", PH["exam"])]

ACKNOWLEDGEMENT = [
    f"I express my sincere gratitude to my project guide, {PH['guide']}, for guidance, encouragement and "
    "critical feedback at every stage of this project. The questions raised during the reviews shaped both "
    "the design of the defense and the way its results are reported.",
    "I am grateful to Dr. S. C. Tamane, Director, Institute of Information and Communication Technology "
    "(IICT), MGM University, Chh. Sambhajinagar, for providing the opportunity to undertake this project under "
    "the Multi-disciplinary minor in Cybersecurity, and to the faculty and staff of IICT for their support.",
    "The project builds on published research and openly available software. I acknowledge the authors of "
    "the papers, vendor guidance and incident reports cited in this report, the maintainers of the open-source "
    "libraries listed in Chapter 5, and Meta for releasing the Llama Prompt Guard 2 classifier (Built with Llama). "
    "The software was developed with the help of an AI coding assistant (Claude Code), working from a written "
    "plan under my direction; the design decisions, reviews and conclusions in this report are my own.",
    "Finally, I thank my family and friends for their patience and support throughout the work.",
]

ABSTRACT = [
    "Applications built on large language models (LLMs) place the developer's instructions, the user's "
    "request and content fetched from emails, web pages or documents into one sequence of text. An attacker "
    "who writes any part of that content can insert instructions that the model may follow. This attack, "
    "prompt injection, is ranked first in the OWASP Top 10 for LLM Applications, and it turns into data "
    "theft once the application can send email or render links.",
    "This project, SecuLayer, is an educational demonstrator and a reusable defense library. Four sandboxed "
    "toy applications (a support chat, an inbox assistant, a page summarizer and a HelpDesk assistant) run "
    "on a real model, GPT-5.4 mini, with fictional data and mock tools. A viewer runs the same attack with and "
    "without SecuLayer and sees the prompt the model received, the layer that stopped the attack and the reason. "
    "SecuLayer has five independent layers: a hidden-text cleaner, screening (rules, the Llama Prompt Guard 2 "
    "classifier and an LLM judge), prompt hardening (spotlighting and a trust policy), a tool guard, and an "
    "output guard. A record-and-replay gateway stores every model call, so the demonstration runs offline with "
    "recorded real responses. The system is built with Python 3.12, FastAPI, React 19 and TypeScript, and is "
    "verified by 378 pytest tests, 55 Vitest component tests and 24 Playwright end-to-end tests.",
    "Without SecuLayer the model resisted the two featured attacks in all three of the first recorded trials. "
    "After two rounds of realistic payload revision, each attack succeeded in 1 of 3 recorded trials: the inbox "
    "assistant emailed Dana's messages to an attacker's address, and the support bot revealed a staff-only "
    "discount code. With SecuLayer both attacks were stopped in 3 of 3 trials, by the hidden-text cleaner and "
    "by screening respectively. Offline, without any model call, the cleaner and screening (rules and "
    "classifier) intervened on 20 of 36 attack cases and raised false alarms on 2 of 20 normal tasks. The full evaluation of all 36 attack cases against "
    "the model is planned and its results are pending.",
]
KEYWORDS = ("prompt injection, large language models, LLM security, defense in depth, spotlighting, "
            "Prompt Guard, tool-call guarding, record and replay")

ABBREVIATIONS = [
    ("AI", "Artificial Intelligence"),
    ("API", "Application Programming Interface"),
    ("ASI", "OWASP Top 10 for Agentic Applications (entry prefix)"),
    ("ASR", "Attack Success Rate"),
    ("ATLAS", "Adversarial Threat Landscape for Artificial-Intelligence Systems (MITRE)"),
    ("BM25", "Best Matching 25 (a ranking function for retrieval)"),
    ("CI", "Confidence Interval"),
    ("CLI", "Command-Line Interface"),
    ("CPU", "Central Processing Unit"),
    ("CSP", "Content Security Policy"),
    ("CSS", "Cascading Style Sheets"),
    ("CVE", "Common Vulnerabilities and Exposures"),
    ("DFD", "Data Flow Diagram"),
    ("HTML", "HyperText Markup Language"),
    ("HTTP", "HyperText Transfer Protocol"),
    ("JSON", "JavaScript Object Notation"),
    ("JSONL", "JSON Lines (one JSON object per line)"),
    ("KB", "Knowledge Base"),
    ("LLM", "Large Language Model"),
    ("MCP", "Model Context Protocol"),
    ("NDJSON", "Newline-Delimited JSON"),
    ("NFKC", "Unicode Normalization Form KC (compatibility composition)"),
    ("ONNX", "Open Neural Network Exchange"),
    ("OWASP", "Open Worldwide Application Security Project"),
    ("RAG", "Retrieval-Augmented Generation"),
    ("SHA-256", "Secure Hash Algorithm, 256-bit"),
    ("SPA", "Single-Page Application"),
    ("TOML", "Tom's Obvious Minimal Language (configuration format)"),
    ("TTL", "Time To Live"),
    ("UI", "User Interface"),
    ("UML", "Unified Modeling Language"),
    ("URL", "Uniform Resource Locator"),
    ("WCAG", "Web Content Accessibility Guidelines"),
]

REFERENCES = {
    "owasp_llm": "OWASP GenAI Security Project, \"OWASP Top 10 for LLM Applications 2026,\" Aug. 3, 2026. "
                 "[Online]. Available: https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/",
    "owasp_agentic": "OWASP GenAI Security Project, \"OWASP Top 10 for Agentic Applications for 2026,\" Dec. 9, 2025. "
                     "[Online]. Available: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/",
    "atlas": "MITRE, \"ATLAS: Adversarial Threat Landscape for Artificial-Intelligence Systems,\" data release 2026.09. "
             "[Online]. Available: https://github.com/mitre-atlas/atlas-data/blob/main/dist/v6/ATLAS-2026.09.yaml",
    "perez": "F. Perez and I. Ribeiro, \"Ignore previous prompt: Attack techniques for language models,\" in "
             "*NeurIPS ML Safety Workshop*, 2022, arXiv:2211.09527.",
    "greshake": "K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, \"Not what you've signed up for: "
                "Compromising real-world LLM-integrated applications with indirect prompt injection,\" in *Proc. 16th ACM "
                "Workshop on Artificial Intelligence and Security (AISec)*, 2023, arXiv:2302.12173.",
    "liu_houyi": "Y. Liu, G. Deng *et al.*, \"Prompt injection attack against LLM-integrated applications,\" "
                 "arXiv:2306.05499, 2023.",
    "liu_formal": "Y. Liu, Y. Jia, R. Geng, J. Jia, and N. Z. Gong, \"Formalizing and benchmarking prompt injection "
                  "attacks and defenses,\" in *Proc. 33rd USENIX Security Symposium*, 2024, arXiv:2310.12815.",
    "yi_bipia": "J. Yi, Y. Xie, B. Zhu, E. Kiciman, G. Sun, X. Xie, and F. Wu, \"Benchmarking and defending against "
                "indirect prompt injection attacks on large language models,\" in *Proc. ACM SIGKDD Conf. Knowledge "
                "Discovery and Data Mining (KDD)*, 2025, arXiv:2312.14197.",
    "hines": "K. Hines, G. Lopez, M. Hall, F. Zarfati, Y. Zunger, and E. Kiciman, \"Defending against indirect prompt "
             "injection attacks with spotlighting,\" arXiv:2403.14720, 2024.",
    "wallace": "E. Wallace, K. Xiao, R. Leike, L. Weng, J. Heidecke, and A. Beutel, \"The instruction hierarchy: "
               "Training LLMs to prioritize privileged instructions,\" arXiv:2404.13208, 2024.",
    "struq": "S. Chen, J. Piet, C. Sitawarin, and D. Wagner, \"StruQ: Defending against prompt injection with structured "
             "queries,\" in *Proc. 34th USENIX Security Symposium*, 2025, arXiv:2402.06363.",
    "llamafirewall": "S. Chennabasappa *et al.*, \"LlamaFirewall: An open source guardrail system for building secure AI "
                     "agents,\" arXiv:2505.03574, 2025.",
    "promptguard": "Meta, \"Llama Prompt Guard 2 model card,\" PurpleLlama repository. [Online]. Available: "
                   "https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Prompt-Guard-2/86M/MODEL_CARD.md",
    "pg_onnx": "gravitee-io, \"Llama-Prompt-Guard-2-22M-onnx,\" Hugging Face model repository, revision "
               "da68d0f6023c7aeaf6b256eec549de295d5e8740. [Online]. Available: "
               "https://huggingface.co/gravitee-io/Llama-Prompt-Guard-2-22M-onnx",
    "willison_dual": "S. Willison, \"The Dual LLM pattern for building AI assistants that can resist prompt injection,\" "
                     "Apr. 25, 2023. [Online]. Available: https://simonwillison.net/2023/Apr/25/dual-llm-pattern/",
    "willison_trifecta": "S. Willison, \"The lethal trifecta for AI agents: private data, untrusted content, and external "
                         "communication,\" Jun. 16, 2025. [Online]. Available: "
                         "https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/",
    "beurer": "L. Beurer-Kellner *et al.*, \"Design patterns for securing LLM agents against prompt injections,\" "
              "arXiv:2506.08837, 2025.",
    "camel": "E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, D. Fabian, C. Kern, C. Shi, A. Terzis, and "
             "F. Tramèr, \"Defeating prompt injections by design,\" arXiv:2503.18813, 2025.",
    "agentdojo": "E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, and F. Tramèr, \"AgentDojo: A "
                 "dynamic environment to evaluate prompt injection attacks and defenses for LLM agents,\" in *NeurIPS "
                 "Datasets and Benchmarks Track*, 2024, arXiv:2406.13352.",
    "nasr": "M. Nasr *et al.*, \"The attacker moves second: Stronger adaptive attacks bypass defenses against LLM "
            "jailbreaks and prompt injections,\" arXiv:2510.09023, Oct. 2025.",
    "rehberger_ascii": "J. Rehberger, \"ASCII Smuggler tool: Crafting invisible text and decoding hidden codes,\" Embrace "
                       "The Red, Jan. 14, 2024. [Online]. Available: "
                       "https://embracethered.com/blog/posts/2024/hiding-and-finding-text-with-unicode-tags/",
    "anthropic_mitigate": "Anthropic, \"Mitigate jailbreaks and prompt injections,\" Claude developer documentation. "
                          "[Online]. Available: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks",
    "anthropic_browser": "Anthropic, \"Mitigating prompt injections in browser use,\" Nov. 24, 2025. [Online]. Available: "
                         "https://www.anthropic.com/research/prompt-injection-defenses",
    "openai_atlas": "OpenAI, \"Continuously hardening ChatGPT Atlas against prompt injection attacks,\" Dec. 22, 2025. "
                    "[Online]. Available: https://openai.com/index/hardening-atlas-against-prompt-injection/",
    "openai_design": "OpenAI, \"Designing AI agents to resist prompt injection,\" Mar. 11, 2026. [Online]. Available: "
                     "https://openai.com/index/designing-agents-to-resist-prompt-injection/",
    "ncsc": "UK National Cyber Security Centre, \"Prompt injection is not SQL injection (it may be worse),\" Dec. 8, 2025. "
            "[Online]. Available: https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection",
    "openai_model": "OpenAI, \"GPT-5.4 mini,\" OpenAI API model documentation. [Online]. Available: "
                    "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
    "openai_fc": "OpenAI, \"Function calling\" and \"Structured outputs,\" OpenAI API guides. [Online]. Available: "
                 "https://developers.openai.com/api/docs/guides/function-calling",
    "inc_bing": "The Verge, report on the hidden rules of Microsoft's Bing Chat (codename \"Sydney\"), "
                "Feb. 14, 2023. [Online]. Available: https://www.theverge.com/23599441/microsoft-bing-ai-sydney-secret-rules",
    "inc_bard": "J. Rehberger, \"Hacking Google Bard - From prompt injection to data exfiltration,\" Embrace The Red, "
                "Nov. 3, 2023. [Online]. Available: https://embracethered.com/blog/posts/2023/google-bard-data-exfiltration/",
    "inc_chevy": "AI Incident Database, \"Chevrolet of Watsonville\" (incident 622), Dec. 2023. [Online]. Available: "
                 "https://incidentdatabase.ai/entities/chevrolet-of-watsonville",
    "inc_slack": "PromptArmor, \"Data exfiltration from Slack AI via indirect prompt injection,\" Aug. 20, 2024. [Online]. "
                 "Available: https://promptarmor.com/resources/data-exfiltration-from-slack-ai-via-indirect-prompt-injection",
    "inc_m365": "J. Rehberger, \"Microsoft Copilot: From prompt injection to exfiltration of personal information,\" "
                "Embrace The Red, Aug. 26, 2024. [Online]. Available: https://embracethered.com/blog/posts/2024/"
                "m365-copilot-prompt-injection-tool-invocation-and-data-exfil-using-ascii-smuggling/",
    "inc_echoleak": "Aim Security (Aim Labs), EchoLeak advisory on a zero-click vulnerability in Microsoft 365 Copilot, "
                    "CVE-2025-32711, Jun. 11, 2025. [Online]. Available: https://www.aim.security/lp/aim-labs-echoleak-blogpost",
    "inc_supabase": "General Analysis, \"Supabase MCP can leak your entire SQL database,\" Jul. 8, 2025. [Online]. Available: "
                    "https://www.generalanalysis.com/blog/supabase-mcp-blog",
    "inc_comet": "Brave, \"Agentic browser security: Indirect prompt injection in Perplexity Comet,\" Aug. 20, 2025. "
                 "[Online]. Available: https://brave.com/blog/comet-prompt-injection/",
    "inc_shadowleak": "Radware Threat Intelligence, ShadowLeak advisory on ChatGPT Deep Research with Gmail, "
                      "Sep. 18, 2025. [Online]. Available: "
                      "https://www.radware.com/blog/threat-intelligence/shadowleak/",
    "inc_forcedleak": "Noma Security, \"ForcedLeak: AI agent risks exposed in Salesforce Agentforce,\" Sep. 25, 2025. "
                      "[Online]. Available: https://noma.security/blog/forcedleak-agent-risks-exposed-in-salesforce-agentforce/",
    "wcag": "W3C, \"Web Content Accessibility Guidelines (WCAG) 2.2,\" W3C Recommendation, Oct. 5, 2023. [Online]. "
            "Available: https://www.w3.org/TR/WCAG22/",
    "rfc2606": "D. Eastlake and A. Panitz, \"Reserved top level DNS names,\" RFC 2606, IETF, Jun. 1999.",
    "wilson": "E. B. Wilson, \"Probable inference, the law of succession, and statistical inference,\" *Journal of the "
              "American Statistical Association*, vol. 22, no. 158, pp. 209-212, 1927.",
    "bm25": "S. Robertson and H. Zaragoza, \"The probabilistic relevance framework: BM25 and beyond,\" *Foundations and "
            "Trends in Information Retrieval*, vol. 3, no. 4, pp. 333-389, 2009.",
}

BODY = CH1 + CH2 + CH3 + CH4 + CH5 + CH6 + CH7 + CH8 + REFERENCES_BLOCK + APPENDICES
