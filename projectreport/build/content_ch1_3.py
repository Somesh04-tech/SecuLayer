"""Chapters 1-3: Introduction, Literature Review, System Analysis."""
from blocks import B, H1, H2, H3, N, P, T

CH1 = [
    H1("1", "Introduction"),
    H2("Introduction"),
    P("""Large language models (LLMs) are now built into customer-support chat windows, email clients, web browsers and
    internal knowledge-base assistants. In each of these applications the program sends the model one prompt that
    combines three kinds of text: instructions written by the application's developer (the system prompt), the request
    typed by the user, and outside content that the application fetched on the user's behalf, such as an email, a web
    page, a retrieved document or the result of a tool call. The model receives all of this as a single sequence of
    tokens. Nothing in that sequence marks which part is allowed to give orders; only the wording suggests it."""),
    P("""**Prompt injection** exploits this property. An attacker writes text that ends up inside the prompt and steers
    the model towards the attacker's goal instead of the application's. In a *direct* injection the attacker types the
    instructions into the application, as Perez and Ribeiro demonstrated with the phrase "ignore previous
    instructions" {ref:perez}. In an *indirect* injection the instructions are planted in content the application later
    reads, for example a hidden line in an email or a paragraph on a web page {ref:greshake}. The OWASP Top 10 for LLM
    Applications 2026 lists prompt injection as LLM01, the first entry {ref:owasp_llm}, and the OWASP Top 10 for Agentic
    Applications lists agent goal hijacking as ASI01 {ref:owasp_agentic}."""),
    P("""The harm grows with what the application can do. Simon Willison describes the *lethal trifecta*: an application
    that has access to private data, is exposed to outside content, and has a way to send data out can be made to leak
    that data {ref:willison_trifecta}. Real incidents follow this pattern. In EchoLeak (CVE-2025-32711) a single external
    email made Microsoft 365 Copilot leak data without the user clicking anything {ref:inc_echoleak}; a message in a public
    Slack channel made Slack AI show a link that carried a private key {ref:inc_slack}; and hidden text on a web page
    hijacked the summarize feature of an AI browser {ref:inc_comet}. Vendors and national agencies state that the
    problem is not solved. OpenAI writes that prompt injection "is unlikely to ever be fully 'solved'" {ref:openai_atlas},
    the UK National Cyber Security Centre argues that it is not comparable to SQL injection because no equivalent of
    parameterised queries exists {ref:ncsc}, and Anthropic reports that even a 1% attack success rate in browser use
    "still represents meaningful risk" {ref:anthropic_browser}."""),
    P("""Written descriptions of prompt injection rarely convey the mechanism to students and developers who have not met
    it. A reader can accept that "hidden text can hijack a model" without seeing why the model obeys it, which defenses
    exist, or how often they work. This project, **SecuLayer**, addresses that gap with a working demonstrator. It
    contains four small, sandboxed toy applications that run on a real model (OpenAI GPT-5.4 mini {ref:openai_model})
    with fictional data and mock tools. A viewer selects an attack, runs it against the unprotected application, and
    sees the exact prompt the model received, with the attacker's text marked in red. The viewer then runs the same
    input, with the same application and the same model, through SecuLayer: a defense module of five independent
    layers that sits between the application and the model. The interface shows which layer stopped the attack and
    why, in plain language, and every outcome comes from recorded real model runs."""),
    H2("Problem Statement"),
    P("""LLM-integrated applications cannot reliably separate trusted instructions from untrusted content, because both
    reach the model as text in one prompt. Consequently, an attacker who controls any part of the outside content, or
    who can type into the application, can cause the application to disclose secrets, send private data to an attacker,
    or present attacker-chosen links and false statements to the user. Existing defenses each address part of the
    problem (filtering inputs, marking untrusted content, training models to prefer developer instructions, or
    restricting tool use), and published research shows that each can be bypassed, especially by attackers who adapt to
    the defense {ref:nasr}."""),
    P("""The problem addressed by this project is therefore twofold. First, to design and implement a layered defense
    that sits outside the model and the application's code, inspects every part of the prompt by its source, controls
    every tool call and every reply, and explains each decision. Second, to demonstrate prompt injection and this
    defense on realistic applications in a way that is reproducible, measurable and honest about the defense's limits,
    so that a technical but non-specialist audience can see the mechanism rather than read about it."""),
    H2("Objectives"),
    P("The objectives of the project are:"),
    N("""To build four toy LLM applications (a customer-support chat, an email assistant with a send tool, a web-page
      summarizer and an internal HelpDesk assistant) that follow design choices common in real applications and
      together cover direct injection, indirect injection, tool hijacking, retrieval poisoning and exfiltration
      through links and images.""",
      """To design and implement SecuLayer, a reusable library of five independent defense layers (hidden-text
      cleaner, screening, prompt hardening, tool guard and output guard) that reports a verdict and a one-line reason
      for every decision and can be switched off layer by layer.""",
      """To assemble an attack library of 12 attacks, each with a primary payload and two variants (36 attack
      cases), and 20 normal-use cases that measure false alarms, using only fictional data and reserved
      `.example` domains {ref:rfc2606}.""",
      """To make every model call reproducible through a record-and-replay gateway, so that the demonstration runs
      offline from recorded real responses and stays within the limits of a free-tier API key.""",
      """To build a web interface, the Attack Lab, that runs each case with and without SecuLayer side by side and
      shows the prompt, the layer verdicts, the reply, the actions taken and what reached the attacker.""",
      """To verify the system with automated unit, integration, component and end-to-end tests, including tests that
      block all network access other than the local server.""",
      """To measure the defense honestly: report attack success with denominators, separate the model's own
      robustness from SecuLayer's effect, and state the attacks the defense cannot stop."""),
    H2("Scope of the Project"),
    P("""The project covers the four toy applications, the five-layer defense library, the record-and-replay model
    gateway, a local web interface and the evaluation method. It runs on a single laptop and binds only to the
    loopback address 127.0.0.1. Replay mode is the default and needs neither a network connection nor an API key;
    live mode calls the OpenAI Responses API with a key kept in a local, git-ignored file. All people, companies and
    domains are fictional: the company is Fernway Outfitters, the user is its operations manager Dana Reyes, and every
    domain ends in `.example`, which is reserved for documentation and can never resolve to a real site
    {ref:rfc2606}."""),
    P("The following are deliberately outside the scope of the project:"),
    B("""Public deployment, user accounts, databases and multiple users.""",
      """Real email, real web browsing and any outbound network request other than the OpenAI API and one pinned
      download of the classifier model.""",
      """Other model providers and local LLMs. The development laptop (an Intel Core i3-6006U with 7.6 GB of RAM and no
      usable GPU) cannot run a useful local model.""",
      """Building the architectural patterns that keep untrusted text away from decisions, such as the dual-LLM
      pattern {ref:willison_dual} and CaMeL {ref:camel}. The report explains them in Chapter 2 but the project does not
      implement them.""",
      """Training or fine-tuning classifiers, automated or adaptive attack generation, jailbreaks aimed at harmful
      content, multi-turn conversations, and injection through images, audio or files."""),
    P("""The build is organised into ten milestones (M1 to M10). At the time of writing, milestones M1 (foundation),
    M2 (defense library and scenario data), M3 (model gateway, toy apps and run API), M4 and M5 (the Attack Lab) are
    complete, and the qualification of the two featured attacks from milestone M6 is complete. The remaining
    qualification of the other ten attacks, the full recordings and the full evaluation (M6 and M7) are pending;
    Chapter 7 states which results are measured and which are not yet available."""),
    P("""The rest of this report is organised as follows. Chapter 2 reviews prompt injection attacks, defenses and
    evaluation methods. Chapter 3 analyses the requirements and feasibility. Chapter 4 presents the system design,
    including the detailed design of each defense layer. Chapter 5 describes the implementation, Chapter 6 the testing,
    and Chapter 7 the results. Chapter 8 concludes and outlines future work."""),
]

CH2 = [
    H1("2", "Literature Review"),
    H2("Review of Existing Systems / Related Work"),
    P("""This chapter reviews the literature in five groups: the attacks themselves, incidents in deployed products,
    detection-based defenses, defenses that change the prompt or the model, and system-level design patterns together
    with the methods used to evaluate all of them. Section 2.2 identifies the gap this project addresses and Section
    2.3 summarises the findings that shaped the design."""),
    H3("Prompt injection attacks"),
    P("""Perez and Ribeiro were among the first to study the problem systematically. They showed that simple
    handcrafted inputs, such as asking a model to ignore its previous prompt, can make GPT-3 based applications abandon
    their task (goal hijacking) or reveal their instructions (prompt leaking) {ref:perez}. Greshake et al. introduced
    *indirect* prompt injection: instructions planted in data that an application retrieves at run time, such as web
    pages and emails. They demonstrated data theft, worm-like spreading and manipulation of answers in real
    LLM-integrated applications, and argued that retrieval turns every piece of fetched content into a potential
    instruction channel {ref:greshake}."""),
    P("""Later work made the attacks more systematic. Liu et al. developed HouYi, a black-box technique that combines a
    framework component, a separator and a disruptor, and found 31 of 36 tested commercial LLM-integrated applications
    vulnerable {ref:liu_houyi}. A second group, also Liu et al., formalised prompt injection attacks and defenses in a
    common framework and benchmarked five attacks and ten defenses across ten LLMs and seven tasks {ref:liu_formal}.
    Rehberger documented "ASCII smuggling", in which Unicode tag characters (U+E0000 to U+E007F) carry text that is
    invisible on screen but still read by some models {ref:rehberger_ascii}. Willison's lethal trifecta explains which
    applications are most at risk: those that combine private data, exposure to outside content and a way to send
    data out {ref:willison_trifecta}."""),
    H3("Incidents in deployed systems"),
    P("""Prompt injection has moved from research to production incidents. {tab:incidents} lists the incidents that the
    project uses as real-world references for its attack library. They cover each channel that SecuLayer's layers
    address: hidden text, instructions in emails and documents, tool misuse, and exfiltration through links and
    images that load without a click."""),
    T("incidents", "Prompt injection incidents in deployed systems used as references for the attack library",
      ["Date", "System and incident", "Technique", "Ref."],
      [["2023-02", "Bing Chat reveals its hidden rules (\"Sydney\")", "Direct injection, system-prompt extraction", "{ref:inc_bing}"],
       ["2023-11", "Google Bard leaks chat history through a shared Google Doc", "Indirect injection, image-URL exfiltration", "{ref:inc_bard}"],
       ["2023-12", "Chevrolet dealer chatbot agrees to sell a car for $1", "Direct injection, role manipulation", "{ref:inc_chevy}"],
       ["2024-08", "Slack AI leaks a private key through a link", "Indirect injection, one-click link exfiltration", "{ref:inc_slack}"],
       ["2024-08", "Microsoft 365 Copilot ASCII smuggling", "Invisible Unicode tag characters", "{ref:inc_m365}"],
       ["2025-06", "EchoLeak, CVE-2025-32711 (Microsoft 365 Copilot)", "Zero-click indirect injection by email", "{ref:inc_echoleak}"],
       ["2025-07", "Supabase MCP agent leaks tokens through a support ticket", "Indirect injection, tool misuse", "{ref:inc_supabase}"],
       ["2025-08", "Perplexity Comet: hidden text hijacks \"Summarize\"", "Hidden text in a web page", "{ref:inc_comet}"],
       ["2025-09", "ShadowLeak: ChatGPT Deep Research with Gmail", "Indirect injection, encoded exfiltration", "{ref:inc_shadowleak}"],
       ["2025-09", "ForcedLeak: Salesforce Agentforce", "Exfiltration through an expired allowlisted domain", "{ref:inc_forcedleak}"]],
      [0.9, 3.0, 2.6, 0.6]),
    P("""Two lessons from these incidents shaped SecuLayer. First, most incidents combine an injection with an *action*:
    sending email, calling a tool, or rendering a link or image whose address carries data. A defense that only
    inspects text is therefore incomplete; actions and outputs need their own checks. Second, several attacks passed
    existing classifiers because the malicious text was worded as an ordinary message to a human reader, which is the
    reason the attack library includes a politely worded "hard case"."""),
    H3("Detection-based defenses"),
    P("""Detection-based defenses inspect text before the model reads it. The simplest are rule filters that look for
    phrases such as "ignore previous instructions"; they are cheap and explainable but brittle against paraphrase,
    other languages and encodings. Learned classifiers generalise better. Meta's Llama Prompt Guard 2 is a family of
    small classifiers (22M and 86M parameters) trained to flag jailbreak and injection attempts {ref:promptguard}; it is one
    of the three guardrails in the open-source LlamaFirewall system, alongside an alignment checker that audits an
    agent's reasoning and a static code analyser {ref:llamafirewall}. An *LLM judge*, a second model that classifies
    content before the main model reads it, can recognise context-dependent instructions that small classifiers miss,
    at the cost of an extra model call and the risk that the judge itself is manipulated. Yi et al. introduced BIPIA,
    the first benchmark for indirect prompt injection, found that existing LLMs are broadly vulnerable, and proposed
    black-box and white-box defenses {ref:yi_bipia}."""),
    H3("Prompt-level and model-level defenses"),
    P("""Prompt-level defenses change how outside content is presented to the model. Hines et al. proposed
    *spotlighting*: delimiting untrusted content, *datamarking* it by replacing whitespace with a special character, or
    encoding it, so that the model can tell data from instructions. In their GPT-family experiments spotlighting reduced
    the attack success rate from above 50% to below 2% with minimal effect on task performance {ref:hines}. Vendor
    guidance gives similar advice: Anthropic recommends screening inputs and keeping untrusted content out of system
    prompts {ref:anthropic_mitigate}, and OpenAI describes agent designs that constrain what injected content can cause
    {ref:openai_design}."""),
    P("""Model-level defenses train the model itself. Wallace et al. proposed the *instruction hierarchy*, training models
    to give developer instructions priority over user messages and user messages priority over tool outputs
    {ref:wallace}; the GPT-5.4 models used in this project are trained in this tradition. Chen et al. proposed StruQ,
    which separates prompts and data into two channels and fine-tunes a model to follow instructions only from the
    prompt channel {ref:struq}. Model-level defenses are effective against known attack styles, but the application
    developer cannot inspect or control them, and their strength varies with the model version and with the attacker's
    wording. This project treats the model's own resistance as a separate, measured factor rather than as part of
    SecuLayer."""),
    H3("System-level design patterns"),
    P("""A third line of work changes the architecture so that untrusted text cannot reach the component that decides
    actions. In Willison's *dual-LLM* pattern, a privileged model that can use tools never sees untrusted text, while a
    quarantined model reads untrusted text but has no tools; ordinary code passes references between them
    {ref:willison_dual}. Beurer-Kellner et al. catalogued six patterns, including action-selector, plan-then-execute,
    LLM map-reduce, dual LLM, code-then-execute and context-minimisation, and analysed their utility and security
    trade-offs {ref:beurer}. CaMeL, by Debenedetti et al., has the model write a program from the trusted request and
    runs it in an interpreter that tracks where every value came from and enforces policies before any tool runs;
    on the AgentDojo benchmark it solved 77% of tasks with provable security, against 84% for an undefended system
    {ref:camel}. These patterns give stronger guarantees than filtering but require rebuilding the application.
    SecuLayer's tool guard borrows two of their ideas in a lighter form: a *task-permission* check that allows
    outbound actions only when the user's own message asks for them (a small plan-then-execute), and a *provenance*
    check that refuses values copied from outside content (a string-matching approximation of CaMeL's data-flow
    tracking)."""),
    H3("Evaluation methods and frameworks"),
    P("""Debenedetti et al. introduced AgentDojo, a dynamic environment of tool-using agent tasks with injection
    attacks, which reports both utility and attack success and has become a common benchmark {ref:agentdojo}. Nasr et al.
    showed why such evaluations must be read with care: using adaptive attacks (gradient-based, reinforcement-learning
    and search-based, plus human red-teaming), they bypassed 12 recent defenses with attack success above 90% for most
    of them, although most of those defenses had originally reported near-zero attack success {ref:nasr}. Frameworks
    give a shared vocabulary: the OWASP Top 10 for LLM Applications {ref:owasp_llm}, the OWASP Top 10 for Agentic
    Applications {ref:owasp_agentic} and MITRE ATLAS {ref:atlas}. Every attack in this project is tagged with its OWASP and
    ATLAS identifiers."""),
    P("""{tab:approaches} compares the defense approaches reviewed above and shows which of them SecuLayer uses."""),
    T("approaches", "Comparison of prompt injection defense approaches",
      ["Approach", "Examples", "Strength", "Limitation", "In SecuLayer"],
      [["Rule filters", "Keyword and pattern rules", "Fast, explainable, no model", "Brittle against paraphrase, languages, encodings", "Screening rules"],
       ["Learned classifier", "Prompt Guard 2 {ref:promptguard}", "Generalises over phrasing; runs on a CPU", "Misses context-dependent and polite injections", "Screening classifier"],
       ["LLM judge", "Second-model screening", "Understands context and intent", "Costs a model call; can itself be targeted", "Screening judge"],
       ["Spotlighting", "Delimiting, datamarking {ref:hines}", "Large reduction in reported ASR", "Lowers, does not remove, the risk", "Prompt hardening"],
       ["Model training", "Instruction hierarchy {ref:wallace}, StruQ {ref:struq}", "Built into the model", "Not controlled by the app developer", "Measured separately"],
       ["Action control", "Least privilege, confirmation", "Stops the harm even if the model is fooled", "People approve convincing requests", "Tool guard"],
       ["Output filtering", "Canary tokens, URL allowlists", "Blocks zero-click leaks", "Finds only what it is told to look for", "Output guard"],
       ["Architecture", "Dual LLM, CaMeL {ref:camel}", "Strong, sometimes provable guarantees", "Requires redesigning the application", "Explained, not built"]],
      [1.1, 1.5, 1.5, 1.7, 1.0]),
    H2("Research Gap"),
    P("""The literature offers many individual defenses and several benchmarks, but the following gaps remain for the
    purpose this project serves:"""),
    B("""**Mechanism is rarely visible.** Papers and benchmarks report aggregate success rates. They seldom show, for a
      single run, the exact prompt the model received, which part came from the attacker, and which check fired. Such a
      view is what a newcomer needs to understand the problem.""",
      """**Defenses are evaluated in isolation.** Most work measures one technique. Few systems combine input
      screening, prompt hardening, action control and output filtering, and attribute each stopped attack to the layer
      responsible, with the ability to switch layers off and see what the next layer catches.""",
      """**The model's own robustness is often conflated with the defense.** Current models resist many classic
      attacks on their own. An honest demonstration has to measure the unprotected baseline on the same model and
      report it, including when the model resists.""",
      """**Utility costs are under-reported.** False alarms on normal requests, added latency and token overhead decide
      whether a defense is usable, but are often missing.""",
      """**Reproducibility.** Results that depend on live model calls change between runs and model versions.
      Recorded runs that can be replayed offline make a demonstration and its evaluation reproducible."""),
    P("""SecuLayer addresses these gaps with a layered defense whose every decision is explained, a side-by-side
    interface on realistic toy applications, a recorded baseline on the same model, explicit normal-use cases, and a
    record-and-replay design."""),
    H2("Summary of Findings"),
    B("""Prompt injection follows from the way LLM applications build prompts, and no published defense removes it
      completely; vendors {ref:openai_atlas}, the NCSC {ref:ncsc} and recent research {ref:nasr} agree on this.""",
      """The damage depends on capability: private data, outside content and a way out together form the lethal
      trifecta {ref:willison_trifecta}. Controlling actions and outputs therefore matters as much as filtering inputs.""",
      """Detection (rules, classifiers, judges) is cheap and explainable but misses context-dependent and politely
      worded injections. Spotlighting and instruction-hierarchy training lower success rates without removing them.""",
      """Architectural patterns such as the dual LLM and CaMeL give the strongest guarantees but require redesigning the
      application; light versions of their ideas (task permission and provenance checks) can be added to existing
      applications.""",
      """Evaluations must include an unprotected baseline, normal-use cases for false alarms, and a statement about
      adaptive attackers, who defeat defenses evaluated only against fixed attacks.""",
      """These findings lead directly to SecuLayer's five-layer design, its separate measurement of model robustness,
      and the "hard cases" that it is expected not to stop."""),
]

CH3 = [
    H1("3", "System Analysis"),
    H2("Requirement Analysis (Functional & Non-Functional)"),
    H3("Users and stakeholders"),
    P("""The system serves four groups. The **viewer** is a technical non-specialist, such as a computer-science
    student, a project evaluator or a developer who uses chatbots, who explores the demonstration without a
    walkthrough. The **presenter** demonstrates the system to an audience from a laptop and a projector in a slot of a
    few minutes. The **developer** (operator) records model runs, runs the evaluation and maintains the code. The
    **evaluator** of the project needs reproducible, honestly reported results. The interface therefore explains every
    term where it first appears, and every rate is shown with its denominator."""),
    H3("Functional requirements"),
    P("""{tab:fr} lists the functional requirements, derived from the implementation plan of the project
    (docs/PLAN.md) and checked against the implemented system. The status column states whether each requirement is
    implemented at the time of writing."""),
    T("fr", "Functional requirements",
      ["ID", "Requirement", "Status"],
      [["FR-1", "Provide four toy LLM applications (support chat, inbox assistant, page summarizer, HelpDesk) built with common naive design choices.", "Implemented"],
       ["FR-2", "Provide 12 attacks with a primary payload and two variants each (36 attack cases) and 20 normal-use cases, with deterministic success and utility checks.", "Implemented"],
       ["FR-3", "Run any case with or without SecuLayer, using the same application code, model and input.", "Implemented"],
       ["FR-4", "Remove hidden HTML, HTML comments and invisible Unicode from outside content, and show what was removed.", "Implemented"],
       ["FR-5", "Screen the user's message and every outside item with rules, a classifier and an LLM judge; block or withhold on intervention.", "Implemented"],
       ["FR-6", "Mark outside content with boundary markers and datamarking, and append a trust policy to the developer instructions.", "Implemented"],
       ["FR-7", "Check every proposed tool call (task permission, recipients, provenance, data) and allow, block or ask the user.", "Implemented"],
       ["FR-8", "Check every reply for the canary, protected values, outside images and outside links before it is shown.", "Implemented"],
       ["FR-9", "Allow each layer to be switched off individually.", "Implemented (library, API and the Layers menu)"],
       ["FR-10", "Record every model call and replay it offline; report \"not recorded\" for missing combinations.", "Implemented"],
       ["FR-11", "Stream run events to the browser and show verdicts, reply, actions and attacker's-server entries.", "Implemented"],
       ["FR-12", "Pause for confirmation when the tool guard asks, and continue on approve or decline.", "Implemented"],
       ["FR-13", "Show the prompt the model received, coloured by source, with injected text marked.", "Implemented (prompt anatomy)"],
       ["FR-14", "Evaluate all cases across configurations and show results with denominators and intervals.", "Method designed; evaluation and Results page pending (M7)"]],
      [0.6, 4.6, 1.8]),
    H3("Non-functional requirements"),
    T("nfr", "Non-functional requirements",
      ["ID", "Category", "Requirement"],
      [["NFR-1", "Availability", "The demonstration works offline in replay mode, with no API key and no network."],
       ["NFR-2", "Safety", "The server binds only to 127.0.0.1; every fake domain ends in .example; replies never load outside images or carry live outside links; toy-app HTML renders only in sandboxed iframes; tests block all non-local network access."],
       ["NFR-3", "Secret handling", "The OpenAI key is read as a secret value from a git-ignored .env file and never appears in logs, recordings, API responses or the browser."],
       ["NFR-4", "Cost", "Development and tests make no API calls; live recording refuses to start if its estimate exceeds the remaining token budget (1,500,000 tokens by default)."],
       ["NFR-5", "Reproducibility", "Dependency versions are pinned; model snapshots are pinned; derived identifiers make prompts identical across runs, so recordings replay exactly."],
       ["NFR-6", "Performance", "SecuLayer's local checks add only milliseconds; the classifier runs on the CPU; the first replay run completes quickly enough for a live presentation."],
       ["NFR-7", "Accessibility", "Text and interface colours meet WCAG AA contrast {ref:wcag}; colour is never the only signal; the main flow works with the keyboard alone."],
       ["NFR-8", "Explainability", "Every layer decision carries a verdict and a one-line reason in plain language."],
       ["NFR-9", "Maintainability", "The defense library imports no web framework, no OpenAI client and no demo code; a test enforces this boundary."],
       ["NFR-10", "Resource limits", "The system runs on a 2-core laptop with 7.6 GB of RAM; tests run with one Playwright worker and at most two Vitest threads."]],
      [0.7, 1.2, 5.1]),
    P("""{tab:nfr} lists the non-functional requirements. Safety and cost requirements receive particular weight
    because the project deliberately builds attacks: every attack targets the project's own toy applications, uses
    fictional data and points only at reserved domains."""),
    H2("Feasibility Study"),
    H3("Technical feasibility"),
    P("""The original brief suggested a small local open-weights model as the unprotected target. The development laptop
    (Intel Core i3-6006U, 2 cores and 4 threads, 7.6 GB of RAM, no usable GPU, about 3 GB of free internal disk) cannot
    run such a model usefully, so the project uses OpenAI's GPT-5.4 mini through the Responses API, pinned to snapshot
    `gpt-5.4-mini-2026-03-17`, on both the unprotected and the protected side. The injection classifier, Llama Prompt
    Guard 2 22M, is used as an int8 ONNX export {ref:pg_onnx} of 72 MB that runs on the CPU with onnxruntime. In the
    planning test on this laptop it scored short inputs in 15 to 80 ms, needed about 0.93 s for a full 512-token
    window, and loaded in 1.6 s. Scores are cached by the SHA-256 of the text in a committed file, so a machine without
    the model still has the recorded scores. All other components (FastAPI, React, BeautifulSoup) are standard and run
    comfortably on the laptop."""),
    H3("Economic feasibility"),
    P("""All software used is free and open source, apart from the OpenAI API, which the developer accesses with a
    free-tier key. The plan estimated about 900 model calls and 1.5 million tokens for full recording and evaluation,
    about US$2 at the list prices of US$0.75 per million input tokens and US$4.50 per million output tokens for
    gpt-5.4-mini. The tools refuse to start a live batch that would exceed the configured token budget, and the spend
    log `data/spend.jsonl` records every live batch. At commit b92144d (milestone M5) the log records 59 live calls, 47,687
    tokens and US$0.0674 in total, about 3.2% of the 1,500,000-token budget."""),
    H3("Operational feasibility"),
    P("""The demonstration starts with one command, `./run.sh`, which installs missing dependencies, builds the front end
    if needed and opens the browser in replay mode at http://127.0.0.1:8765. Replay mode makes the presentation
    independent of the network and of the model's run-to-run variation, while SecuLayer's own checks still run live,
    so switching a layer off produces a genuine new decision. Live mode is one flag away (`./run.sh --live`) for
    viewers who want to try new inputs."""),
    H3("Schedule feasibility"),
    P("""The work is divided into ten milestones, each ending in an automated acceptance check and a commit.
    {tab:milestones} shows their status at commit b92144d. Milestones were ordered so that the demonstration becomes
    presentable after M5, with a fixed order of features to cut if time ran short."""),
    T("milestones", "Project milestones and their status at commit b92144d",
      ["ID", "Milestone", "Status"],
      [["M1", "Foundation: scaffold, run script, test harness, design tokens, app shell", "Done"],
       ["M2", "SecuLayer core library and scenario data", "Done"],
       ["M3", "Model gateway, toy apps, run API and first recordings", "Done (including the Layers-menu recordings)"],
       ["M4", "Attack Lab, part 1: run each case both ways", "Done"],
       ["M5", "Attack Lab, part 2: prompt anatomy, Layers menu, glossary, timeline", "Done"],
       ["M6", "Attack qualification and full recordings", "Featured attacks qualified; remaining 10 attacks pending"],
       ["M7", "Evaluation and Results page", "Not started"],
       ["M8", "Explainer pages and Sandbox", "Not started"],
       ["M9", "Accessibility, presenter readiness and polish", "Not started"],
       ["M10", "Final verification", "Not started"]],
      [0.6, 4.4, 2.0]),
    H3("Legal and ethical feasibility"),
    P("""The project builds working attacks, so its ethical constraints are part of the design. Every attack targets only
    the project's own toy applications; all people and companies are fictional; every domain is under `.example`
    {ref:rfc2606}; the attacker's "server" is a simulated panel in the interface; and the mock `send_email` tool sends
    nothing. The demonstration is about hijacking an application's goals, not about producing harmful content.
    Prompt Guard 2 is distributed under the Llama 4 Community License, which requires the "Built with Llama" credit
    that the project displays."""),
    H2("System Specifications (Hardware/Software)"),
    P("""{tab:hw} lists the hardware on which the system was developed and is presented, and {tab:sw} lists the software
    stack with the exact pinned versions from the project's `pyproject.toml` and `web/package.json`. Each dependency is
    the newest release that was at least two weeks old on 2026-10-23, a cheap supply-chain precaution for a security
    project."""),
    T("hw", "Hardware specification of the development and presentation machine",
      ["Component", "Specification"],
      [["Processor", "Intel Core i3-6006U, 2 cores, 4 threads"],
       ["Memory", "7.6 GB RAM"],
       ["GPU", "None usable for model inference"],
       ["Storage", "Internal disk (about 4 GB free) plus an external NTFS drive that holds the repository, environments, caches and the classifier"],
       ["Network", "Needed only for live mode, recording and the one-time classifier download"],
       ["Display", "Laptop screen and projector; designed for 1440×900 and 1280×720"]],
      [1.6, 5.4]),
    T("sw", "Software stack and pinned versions",
      ["Layer", "Software (version)"],
      [["Language and tooling", "Python 3.12 (uv 0.12, hatchling 1.32.4); Node 22 with npm 10"],
       ["Backend", "FastAPI 0.143.0, uvicorn 0.54.0, pydantic 2.14.0, pydantic-settings 2.15.0, typer 0.27.3, httpx 0.28.1"],
       ["Model access", "openai 3.28.0 (Responses API); models gpt-5.4-mini-2026-03-17 and gpt-5.4-2026-03-05"],
       ["Classifier", "Llama Prompt Guard 2 22M (int8 ONNX), onnxruntime 1.31.0, tokenizers 0.23.3, numpy 2.5.3"],
       ["Text processing", "beautifulsoup4 4.15.0 (HTML parsing), Python unicodedata and base64"],
       ["Frontend", "React 19.3.0, react-router 8.4.0, radix-ui 1.7.0, lucide-react 1.54.0, motion 14.1.0, react-markdown 10.1.0, remark-gfm 4.0.1"],
       ["Build and styling", "TypeScript 6.0.3, Vite 8.3.4, Tailwind CSS 4.3.3, Atkinson Hyperlegible Next and Mono fonts"],
       ["Testing and quality", "pytest 9.1.1, ruff 0.17.0, mypy 2.4.0 (strict), Vitest 5.0.3, Playwright 1.64.0, axe-core 4.13.0, ESLint 9.39.5, openapi-typescript 7.13.0"],
       ["Operating system", "Linux (Linux Mint) on the laptop"]],
      [1.6, 5.4]),
]
