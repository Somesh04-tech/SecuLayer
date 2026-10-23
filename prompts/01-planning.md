You're the planning agent for SecuLayer, a new cybersecurity project. Your job in this session is the implementation plan, not code. A separate build agent (Claude Opus 5.5 at high effort, in Claude Code) will implement the plan over several sessions, each starting with no memory of this conversation, so the plan has to stand on its own. The repository is new: apart from this brief (saved at `prompts/01-planning.md`), it is empty.

<goal>
SecuLayer is an interactive web app about prompt injection in LLM applications. It has two jobs:

1. Show the problem: how an LLM-powered app gets hijacked by injected instructions, both ones an attacker types directly and ones hidden inside content the app reads (a web page, an email, a document, a tool result).
2. Show a solution: SecuLayer itself, a defense layer between the app and the model that stops those same attacks and explains which check caught each one and why.

The UI is the most important part of the project. The subject is technical; the interface's job is to make it obvious to someone seeing it for the first time.
</goal>

<audience_and_success>
Assume viewers are technical but not security specialists: a CS student, a project evaluator, a developer who uses chatbots but has never thought about prompt injection. Confirm this in the interview.

The project succeeds when:
- A first-time viewer, with no walkthrough, can pick an attack, run it against the unprotected app, see the hijacked result with the injected instructions highlighted, run the same input through SecuLayer, and understand in plain language what was blocked and why.
- The comparison is fair: same model, same input, same app. Only SecuLayer differs.
- It can be presented live without risk: one command starts it on my Linux machine, and a demo mode works with no network access and no API keys.
- The security content is accurate and honest. It shows defense in depth, reports measured results rather than claims, and is upfront that no defense fully solves prompt injection, including at least one attack that stays hard to stop, with the reason.
</audience_and_success>

<ui_direction>
Very clean, white, and easy to understand:
- Pure white background, generous whitespace, one accent color, and a few semantic colors used only for meaning and kept consistent on every screen (for example: red for injected or malicious text, amber for untrusted outside content, green for a safe outcome).
- Plain language first. Explain each technical term where it first appears (inline, a tooltip, or an expandable "what's happening here").
- Show the mechanism, not just the outcome. The central teaching visual is the full prompt the model actually receives, color-coded by source (developer instructions, user input, outside content, injected instructions), so viewers see why the model gets confused. Show the defense as a sequence of layers, each with its verdict and a one-line reason.
- Polished but restrained: it should look professionally designed, with considered empty, loading, and error states, clear hover and focus states, and motion only where it helps understanding.
- Accessible (WCAG AA contrast, keyboard navigation) and legible on both a laptop screen and a projector.

Asked for frontend work without specific direction, models fall back on a few default styles, so avoid these: cream, beige, or off-white backgrounds; dark "hacker terminal" themes with neon green; purple-to-blue gradients; glassmorphism; italic accent words in headlines; numbered "01 / 02 / 03" section labels; monospace for decorative labels (monospace is right for actual prompt and code text); pill-shaped buttons everywhere; emoji as icons; padlock-and-shield hero art; a default font such as Inter, Roboto, Arial, or the system stack (choose a typeface with some character that stays highly legible). Pin the look down in the plan as concrete design tokens and component choices so the build agent implements one consistent design rather than improvising per screen, and tell it to extend this list if its first screens drift toward a different default.
</ui_direction>

<security_content>
The items below are starting points: keep, change, or replace them based on what teaches best. A focused set of scenarios and attacks, each explained well, beats a long list.

Scenarios (small sandboxed toy apps with fake data and mock tools), for example:
- a support chatbot whose system prompt holds a fake secret, such as a discount code or API key;
- an email assistant that reads an inbox and can send email, where an incoming message carries hidden instructions;
- a summarizer for web pages or documents that contain invisible text;
- a knowledge-base (RAG) assistant with one poisoned document.

At least one scenario should show injection triggering an action (a tool call, or data leaving through a link or markdown image) rather than just an odd reply, because that is where real-world damage happens. Simulate the attacker's side as well, for example an "attacker's server" panel showing what would have leaked. Nothing makes real outbound requests.

Attack techniques to draw from: instruction override, role-play and persona switching, fake system messages and delimiter breaking, system-prompt extraction, hidden text (CSS-hidden text, HTML comments, zero-width or Unicode tag characters), encoding and obfuscation (Base64, other languages), payload splitting, markdown image or link exfiltration, tool-call hijacking, and document or RAG poisoning. For each attack, the plan gives the attacker's goal, a payload sketch, a plain-language explanation, the expected result with and without SecuLayer, and the layer expected to catch it.

Defense layers to choose from and combine: input screening (pattern rules plus a pre-trained injection classifier or a small LLM judge with structured output); marking or encoding untrusted content so the model reads it as data rather than instructions (delimiting, datamarking, JSON encoding), backed by a system prompt that states the trust policy; least-privilege tools with human confirmation for sensitive actions; output checks (canary tokens for system-prompt leaks, secret and PII detection, blocking exfiltration links and images); and architectural patterns such as dual-LLM or plan-then-execute, explained even if not built. Each layer is toggleable in the UI so viewers can see which layer catches what. Structure SecuLayer as a self-contained module with a clear interface, so it reads as a reusable solution rather than demo glue.

Evaluation: a reproducible runner that sends an attack set and a benign set through the app with and without SecuLayer and reports attack success rate, per-layer catch rate, false positives on benign inputs, and added latency, with results shown in the UI. Judge attack success with deterministic checks where possible (a canary string in the output, a mock tool called with the attacker's arguments) rather than another model's opinion.

Ground the content in current sources: the OWASP Top 10 for LLM Applications, MITRE ATLAS, Anthropic's guide "Mitigate jailbreaks and prompt injections" (https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks), the "lethal trifecta" framing (private data plus untrusted content plus a way to send data out), and the research behind the patterns above (Spotlighting, the dual-LLM pattern, CaMeL, "Design Patterns for Securing LLM Agents against Prompt Injections"). The field moves fast: check current versions of tools, classifier models, and libraries before choosing them, and give a source link for every real-world incident the app cites.
</security_content>

<open_decisions>
The plan has to settle these explicitly:
- Which model powers the demo. Frontier models resist many naive injections (Anthropic's docs say Claude Opus 5.5 resists indirect prompt injection better than any earlier Opus model), so a strong model used as the vulnerable target may not get hijacked on stage. Decide how the unprotected side is powered (a small open-weights model run locally, a deliberately naive app design, or a mix), and add a deterministic replay mode built from recorded real runs so the presentation never depends on live model behavior. Present model-level robustness honestly, as one layer among several.
- Keys and cost: API keys live only in a local `.env` and never reach the browser; demo mode needs no keys.
- Tech stack: recommend one and say why, weighing how good the UI can look, how simple it stays for a solo developer (me, unless I say otherwise), and whether the chosen defenses need a Python ML runtime.
</open_decisions>

<how_to_work>
1. Interview me first. Ask only questions whose answers would change the plan, batched, each with your recommended default (use the AskUserQuestion tool if you have it). Likely topics: what the project is for (course project, hackathon, portfolio, talk) and its deadline; what model access I have (API keys and budget, or a machine that can run local models); stack preferences; whether it must be publicly deployed. Skip the obvious and dig into the hard parts I may not have considered. Anything I leave unanswered: use your default and list it under assumptions.
2. Research whatever depends on the current state of tools, and note the sources you relied on.
3. Write the plan.

Plan what I asked for at the scope I intended: a focused, polished, reliable demo. Keep the architecture as simple as the requirements allow, with no user accounts, databases, or deployment infrastructure unless a requirement needs them. If you think part of this request is mistaken or there's a better approach, say so in a sentence and plan the better option. Use subagents only for genuinely independent research tracks.
</how_to_work>

<deliverable>
One Markdown document saved as `docs/PLAN.md`. If you're in plan mode, present it for approval first; once I approve, save it to that path and stop there. Implementation happens in a separate session.

It contains:
- Summary: what SecuLayer is, who it's for, what the demo proves.
- Decisions and assumptions, each with its reason; mark those I should confirm.
- User experience: the main demo flow from the viewer's side, each screen and its purpose, a text wireframe of each key screen, and a 3-5 minute demo script for presenting it live.
- Design system: color tokens with hex values, typefaces and type scale, spacing, radii, component inventory, and the avoid-list.
- Scenarios and attack library, in the detail described above.
- SecuLayer architecture: the request flow; each layer (how it decides, how it can fail, how its verdict appears in the UI); the module interface.
- Evaluation: datasets, metrics, how to run it, how results appear in the UI.
- Tech stack and repository layout: frameworks and key libraries with verified versions, folder structure, environment variables, run and test commands.
- Build milestones, in order. Each ends in a runnable, demoable state with acceptance checks the build agent can run itself (test commands, the evaluation run, browser or screenshot checks of key screens) and a git commit. The first milestone lays the foundation: scaffold, one-command run script, test harness, a short `CLAUDE.md` with run and test commands and conventions, and a progress file the build agent updates at the end of every session. The last ends with an end-to-end run of the demo script in both replay and live mode.
- Out of scope.
- Risks and mitigations.
- Build kickoff prompt: a short message I can paste into a fresh build session that points the build agent to the plan, the progress file, and the first milestone.

Write for a reader who hasn't seen this conversation: complete sentences, terms defined, no shorthand coined during planning. Make it as long as the build agent needs to work without guessing, and no longer: no filler sections or repeated summaries.
</deliverable>
