/**
 * Every source the app cites, exactly as listed in docs/PLAN.md §12 (checked 2026-10-23).
 * web/tests/sources.test.ts asserts the URLs here are exactly the URLs in §12.
 *
 * MITRE ATLAS technique pages follow the pattern https://atlas.mitre.org/techniques/<ID>;
 * §12 gives that pattern rather than one page per technique, so it appears here as its base
 * URL plus the technique IDs the demo uses.
 */

export type SourceGroup = "framework" | "guidance" | "research" | "incident" | "credit";

export interface SourceLink {
  url: string;
  /** Short label when an entry has more than one link, e.g. "PDF". */
  label?: string;
}

export interface Source {
  id: string;
  title: string;
  /** Publisher or authors, as plain text. */
  by: string;
  /** As written in §12: a full date, a month, a year, or empty when §12 gives none. */
  date: string;
  links: SourceLink[];
  group: SourceGroup;
  /** One line on what it is or why the app cites it. */
  note?: string;
}

export const SOURCES_CHECKED_ON = "2026-10-23";

export const ATLAS_TECHNIQUES: { id: string; name: string }[] = [
  { id: "AML.T0051", name: "LLM Prompt Injection (.000 Direct, .001 Indirect)" },
  { id: "AML.T0053", name: "AI Agent Tool Invocation" },
  { id: "AML.T0054", name: "LLM Jailbreak" },
  { id: "AML.T0056", name: "Extract LLM System Prompt" },
  { id: "AML.T0057", name: "LLM Data Leakage" },
  { id: "AML.T0068", name: "LLM Prompt Obfuscation" },
  { id: "AML.T0070", name: "RAG Poisoning" },
  { id: "AML.T0071", name: "False RAG Entry Injection" },
  { id: "AML.T0077", name: "LLM Response Rendering" },
  { id: "AML.T0086", name: "Exfiltration via AI Agent Tool Invocation" },
];

export const SOURCES: Source[] = [
  // Frameworks
  {
    id: "owasp-llm-2026",
    title: "OWASP Top 10 for LLM Applications 2026",
    by: "OWASP GenAI Security Project",
    date: "2026-08-03",
    group: "framework",
    links: [
      { url: "https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/" },
      { url: "https://genai.owasp.org/download/56857/?tmstv=1785822482", label: "PDF" },
      {
        url: "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
        label: "Prompt Injection web entry (still the 2025 text)",
      },
    ],
    note: "Used: LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure, LLM03 Excessive Agency, LLM05 Data and Model Poisoning, LLM07 Misinformation, LLM08 Hidden Context Exposure, LLM09 Vector and Embedding Weaknesses, LLM10 Improper Output Handling.",
  },
  {
    id: "owasp-agentic-2026",
    title: "OWASP Top 10 for Agentic Applications 2026",
    by: "OWASP GenAI Security Project",
    date: "2025-12-09",
    group: "framework",
    links: [
      { url: "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/" },
    ],
    note: "Used: ASI01 Agent Goal Hijack, ASI02 Tool Misuse and Exploitation, ASI09 Human-Agent Trust Exploitation.",
  },
  {
    id: "mitre-atlas",
    title: "MITRE ATLAS, data release 2026.09",
    by: "MITRE",
    date: "2026.09",
    group: "framework",
    links: [
      { url: "https://github.com/mitre-atlas/atlas-data/blob/main/dist/v6/ATLAS-2026.09.yaml" },
      { url: "https://atlas.mitre.org/techniques/", label: "Technique pages" },
    ],
    note: "Technique pages live at atlas.mitre.org/techniques/<ID>.",
  },

  // Vendor and government guidance
  {
    id: "anthropic-mitigate",
    title: "Mitigate jailbreaks and prompt injections",
    by: "Anthropic",
    date: "",
    group: "guidance",
    links: [
      {
        url: "https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks",
      },
    ],
  },
  {
    id: "anthropic-browser-use",
    title: "Mitigating prompt injections in browser use",
    by: "Anthropic",
    date: "2025-11-24",
    group: "guidance",
    links: [{ url: "https://www.anthropic.com/research/prompt-injection-defenses" }],
  },
  {
    id: "openai-atlas-hardening",
    title: "Continuously hardening ChatGPT Atlas against prompt injection attacks",
    by: "OpenAI",
    date: "2025-12-22",
    group: "guidance",
    links: [{ url: "https://openai.com/index/hardening-atlas-against-prompt-injection/" }],
  },
  {
    id: "openai-designing-agents",
    title: "Designing AI agents to resist prompt injection",
    by: "OpenAI",
    date: "2026-03-11",
    group: "guidance",
    links: [{ url: "https://openai.com/index/designing-agents-to-resist-prompt-injection/" }],
  },
  {
    id: "openai-agent-safety",
    title: "Safety in building agents",
    by: "OpenAI",
    date: "",
    group: "guidance",
    links: [{ url: "https://developers.openai.com/api/docs/guides/agent-builder-safety" }],
    note: "Part of Agent Builder, which shuts down on 2026-11-30, so the page may move.",
  },
  {
    id: "ncsc",
    title: "Prompt injection is not SQL injection (it may be worse)",
    by: "UK NCSC",
    date: "2025-12-08",
    group: "guidance",
    links: [{ url: "https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection" }],
  },
  {
    id: "openai-api-docs",
    title: "OpenAI API documentation",
    by: "OpenAI",
    date: "",
    group: "guidance",
    links: [
      { url: "https://developers.openai.com/api/docs/models/gpt-5.4-mini", label: "GPT-5.4 mini" },
      { url: "https://developers.openai.com/api/docs/models/gpt-5.4", label: "GPT-5.4" },
      {
        url: "https://developers.openai.com/api/docs/guides/latest-model/gpt-5.4.md",
        label: "GPT-5.4 guide",
      },
      {
        url: "https://developers.openai.com/api/docs/guides/function-calling",
        label: "Function calling",
      },
      {
        url: "https://developers.openai.com/api/docs/guides/structured-outputs",
        label: "Structured outputs",
      },
      { url: "https://developers.openai.com/api/docs/deprecations", label: "Deprecations" },
    ],
  },

  // Research and essays
  {
    id: "greshake-2023",
    title: "Not what you've signed up for",
    by: "Greshake et al.",
    date: "2023",
    group: "research",
    links: [{ url: "https://arxiv.org/abs/2302.12173" }],
  },
  {
    id: "hines-2024",
    title: "Defending Against Indirect Prompt Injection Attacks With Spotlighting",
    by: "Hines et al.",
    date: "2024",
    group: "research",
    links: [{ url: "https://arxiv.org/abs/2403.14720" }],
  },
  {
    id: "wallace-2024",
    title: "The Instruction Hierarchy",
    by: "Wallace et al.",
    date: "2024",
    group: "research",
    links: [{ url: "https://arxiv.org/abs/2404.13208" }],
  },
  {
    id: "willison-dual-llm",
    title: "The Dual LLM pattern",
    by: "Simon Willison",
    date: "2023-04-25",
    group: "research",
    links: [{ url: "https://simonwillison.net/2023/Apr/25/dual-llm-pattern/" }],
  },
  {
    id: "camel-2025",
    title: "Defeating Prompt Injections by Design (CaMeL)",
    by: "Debenedetti et al.",
    date: "2025",
    group: "research",
    links: [{ url: "https://arxiv.org/abs/2503.18813" }],
  },
  {
    id: "beurer-kellner-2025",
    title: "Design Patterns for Securing LLM Agents against Prompt Injections",
    by: "Beurer-Kellner et al.",
    date: "2025",
    group: "research",
    links: [{ url: "https://arxiv.org/abs/2506.08837" }],
  },
  {
    id: "agentdojo-2024",
    title: "AgentDojo",
    by: "Debenedetti et al.",
    date: "2024",
    group: "research",
    links: [{ url: "https://arxiv.org/abs/2406.13352" }],
  },
  {
    id: "nasr-2025",
    title: "The Attacker Moves Second",
    by: "Nasr et al.",
    date: "2025-10-10",
    group: "research",
    links: [{ url: "https://arxiv.org/abs/2510.09023" }],
  },
  {
    id: "willison-trifecta",
    title: "The lethal trifecta for AI agents",
    by: "Simon Willison",
    date: "2025-06-16",
    group: "research",
    links: [{ url: "https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/" }],
  },
  {
    id: "liu-2024",
    title: "Formalizing and Benchmarking Prompt Injection Attacks and Defenses",
    by: "Liu et al. (USENIX Security 2024)",
    date: "2024",
    group: "research",
    links: [{ url: "https://arxiv.org/abs/2310.12815" }],
  },
  {
    id: "rehberger-ascii-smuggler",
    title: "ASCII Smuggler Tool: Crafting Invisible Text and Decoding Hidden Codes",
    by: "Johann Rehberger",
    date: "2024-01-14",
    group: "research",
    links: [
      {
        url: "https://embracethered.com/blog/posts/2024/hiding-and-finding-text-with-unicode-tags/",
      },
    ],
  },

  // Incidents
  {
    id: "bing-sydney",
    title: "Bing Chat reveals its hidden rules (“Sydney”)",
    by: "The Verge",
    date: "2023-02",
    group: "incident",
    note: "The original tweet is deleted.",
    links: [{ url: "https://www.theverge.com/23599441/microsoft-bing-ai-sydney-secret-rules" }],
  },
  {
    id: "webpilot",
    title: "ChatGPT WebPilot plugin: image exfiltration",
    by: "Johann Rehberger",
    date: "2023-05-16",
    group: "incident",
    links: [
      {
        url: "https://embracethered.com/blog/posts/2023/chatgpt-webpilot-data-exfil-via-markdown-injection/",
      },
      {
        url: "https://embracethered.com/blog/posts/2023/openai-data-exfiltration-first-mitigations-implemented/",
        label: "The later mitigation",
      },
    ],
  },
  {
    id: "bard",
    title: "Google Bard: exfiltration through a shared Google Doc",
    by: "Johann Rehberger",
    date: "2023-11-03",
    group: "incident",
    links: [{ url: "https://embracethered.com/blog/posts/2023/google-bard-data-exfiltration/" }],
  },
  {
    id: "chevrolet",
    title: "Chevrolet of Watsonville's chatbot and the “$1 Tahoe”",
    by: "Chris Bakke; AI Incident Database",
    date: "2023-12-17",
    group: "incident",
    links: [
      { url: "https://twitter.com/ChrisJBakke/status/1736533308849443121" },
      {
        url: "https://incidentdatabase.ai/entities/chevrolet-of-watsonville",
        label: "AI Incident Database",
      },
    ],
  },
  {
    id: "slack-ai",
    title: "Slack AI: data exfiltration from private channels",
    by: "PromptArmor",
    date: "2024-08-20",
    group: "incident",
    links: [
      {
        url: "https://promptarmor.com/resources/data-exfiltration-from-slack-ai-via-indirect-prompt-injection",
      },
    ],
  },
  {
    id: "m365-ascii",
    title: "Microsoft 365 Copilot: ASCII smuggling",
    by: "Johann Rehberger",
    date: "2024-08-26",
    group: "incident",
    links: [
      {
        url: "https://embracethered.com/blog/posts/2024/m365-copilot-prompt-injection-tool-invocation-and-data-exfil-using-ascii-smuggling/",
      },
    ],
  },
  {
    id: "github-mcp",
    title: "GitHub MCP: “toxic agent flow”",
    by: "Invariant Labs",
    date: "2025-05-26",
    group: "incident",
    links: [{ url: "https://invariantlabs.ai/blog/mcp-github-vulnerability" }],
  },
  {
    id: "echoleak",
    title: "EchoLeak, CVE-2025-32711",
    by: "Aim Security; Microsoft",
    date: "2025-06-11",
    group: "incident",
    links: [
      { url: "https://www.aim.security/lp/aim-labs-echoleak-blogpost" },
      {
        url: "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2025-32711",
        label: "Microsoft advisory",
      },
    ],
  },
  {
    id: "supabase-mcp",
    title: "Supabase MCP: token leak through a support ticket",
    by: "General Analysis",
    date: "2025-07",
    group: "incident",
    links: [{ url: "https://www.generalanalysis.com/blog/supabase-mcp-blog" }],
  },
  {
    id: "copilot-rce",
    title: "GitHub Copilot remote code execution, CVE-2025-53773",
    by: "Johann Rehberger",
    date: "2025-08-12",
    group: "incident",
    links: [
      {
        url: "https://embracethered.com/blog/posts/2025/github-copilot-remote-code-execution-via-prompt-injection/",
      },
    ],
  },
  {
    id: "comet",
    title: "Perplexity Comet: hidden text hijacks “Summarize”",
    by: "Brave",
    date: "2025-08-20",
    group: "incident",
    links: [{ url: "https://brave.com/blog/comet-prompt-injection/" }],
  },
  {
    id: "shadowleak",
    title: "ShadowLeak: ChatGPT Deep Research with Gmail",
    by: "Radware",
    date: "2025-09-18",
    group: "incident",
    links: [{ url: "https://www.radware.com/blog/threat-intelligence/shadowleak/" }],
  },
  {
    id: "forcedleak",
    title: "ForcedLeak: Salesforce Agentforce",
    by: "Noma Security",
    date: "2025-09-25",
    group: "incident",
    links: [
      {
        url: "https://noma.security/blog/forcedleak-agent-risks-exposed-in-salesforce-agentforce/",
      },
    ],
  },
  {
    id: "gemini-trifecta",
    title: "The Gemini Trifecta",
    by: "Tenable",
    date: "2025-09-30",
    group: "incident",
    links: [
      {
        url: "https://www.tenable.com/blog/the-trifecta-how-three-new-gemini-vulnerabilities-in-cloud-assist-search-model-and-browsing",
      },
    ],
  },
  {
    id: "claude-cowork",
    title: "Claude Cowork: file exfiltration",
    by: "PromptArmor",
    date: "2026-01-14",
    group: "incident",
    links: [{ url: "https://www.promptarmor.com/resources/claude-cowork-exfiltrates-files" }],
  },
  {
    id: "clinejection",
    title: "Clinejection, followed by an unauthorised npm release",
    by: "Adnan Khan; Cline",
    date: "2026-02",
    group: "incident",
    links: [
      { url: "https://adnanthekhan.com/posts/clinejection/" },
      {
        url: "https://cline.bot/blog/post-mortem-unauthorized-cline-cli-npm",
        label: "Post-mortem",
      },
    ],
  },
  {
    id: "grafana-ghost",
    title: "GrafanaGhost",
    by: "Noma Security",
    date: "2026-04-07",
    group: "incident",
    links: [{ url: "https://noma.security/blog/grafana-ghost" }],
  },
  {
    id: "comment-and-control",
    title: "Comment and Control: credential theft through coding agents",
    by: "oddguan",
    date: "2026-04-15",
    group: "incident",
    links: [
      {
        url: "https://oddguan.com/blog/comment-and-control-prompt-injection-credential-theft-claude-code-gemini-cli-github-copilot/",
      },
    ],
  },
  {
    id: "cosnitch",
    title: "CoSnitch, CVE-2026-24301",
    by: "Varonis; Microsoft",
    date: "2026-08-18",
    group: "incident",
    links: [
      { url: "https://www.varonis.com/blog/cosnitch" },
      {
        url: "https://msrc.microsoft.com/update-guide/vulnerability/CVE-2026-24301",
        label: "Microsoft advisory",
      },
    ],
  },

  // Credits
  {
    id: "prompt-guard",
    title: "Llama Prompt Guard 2 22M",
    by: "Meta",
    date: "",
    group: "credit",
    note: "The screening layer's classifier. Built with Llama: licensed under the Llama 4 Community License.",
    links: [
      {
        url: "https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Prompt-Guard-2/86M/MODEL_CARD.md",
        label: "Model card",
      },
      {
        url: "https://huggingface.co/gravitee-io/Llama-Prompt-Guard-2-22M-onnx",
        label: "The ONNX export used (gravitee-io)",
      },
      {
        url: "https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M",
        label: "The official, gated model",
      },
    ],
  },
];

/** Quotes the Limits page uses, each tied to its source. */
export const QUOTES = {
  openaiAtlas: {
    sourceId: "openai-atlas-hardening",
    text: "Prompt injection, much like scams and social engineering on the web, is unlikely to ever be fully ‘solved’.",
    by: "OpenAI, December 2025",
  },
  anthropicBrowser: {
    sourceId: "anthropic-browser-use",
    text: "A 1% attack success rate—while a significant improvement—still represents meaningful risk.",
    by: "Anthropic, November 2025",
  },
} as const;

export function sourceById(id: string): Source {
  const found = SOURCES.find((s) => s.id === id);
  if (!found) throw new Error(`Unknown source ${id}`);
  return found;
}

/** Every URL in the list, for the §12 consistency test. */
export function allSourceUrls(): string[] {
  return SOURCES.flatMap((s) => s.links.map((l) => l.url));
}

/** "https://www.example.com/a" → "example.com" */
export function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
