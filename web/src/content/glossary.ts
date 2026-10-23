/** Glossary text for the Term tooltip (docs/PLAN.md §3.5). */
export const glossary = {
  prompt: {
    term: "Prompt",
    definition:
      "Everything the model reads in one request: the developer's instructions, the user's message, and any outside content the app adds.",
  },
  developerInstructions: {
    term: "Developer instructions (the system prompt)",
    definition:
      "Text the app's builders write to tell the model how to behave. Users normally don't see it.",
  },
  promptInjection: {
    term: "Prompt injection",
    definition:
      "Text written by an attacker that ends up in the prompt and makes the model follow the attacker's instructions instead of the app's.",
  },
  directInjection: {
    term: "Direct injection",
    definition: "The attacker types the instructions into the app themselves.",
  },
  indirectInjection: {
    term: "Indirect injection",
    definition:
      "The instructions are hidden in content the app reads on the user's behalf, such as an email, a web page or a document.",
  },
  outsideContent: {
    term: "Outside content",
    definition:
      "Anything the app fetched from elsewhere: emails, web pages, documents, tool results. Anyone can write it, so it can't be trusted to give instructions.",
  },
  toolCall: {
    term: "Tool call",
    definition: 'The model asking the app to run a function it provides, such as "send an email".',
  },
  exfiltration: {
    term: "Exfiltration",
    definition:
      "Getting private data out to an attacker, for example inside a link or an image's web address.",
  },
  canaryToken: {
    term: "Canary token",
    definition:
      "A random marker hidden in the developer instructions. If it ever appears in a reply, the instructions have leaked.",
  },
  classifier: {
    term: "Classifier",
    definition:
      'A small machine-learning model trained to score text as "looks like an attack" or "looks normal".',
  },
  llmJudge: {
    term: "LLM judge",
    definition:
      "A second language model that inspects content for injected instructions before the main model reads it.",
  },
  spotlighting: {
    term: "Spotlighting",
    definition:
      "Marking outside content, with boundary markers and a symbol between words, so the model can tell it apart from instructions.",
  },
  falseAlarm: {
    term: "False alarm",
    definition: "A normal request that a defense wrongly blocks. Also called a false positive.",
  },
  attackSuccessRate: {
    term: "Attack success rate",
    definition: "The share of attack runs in which the attacker got what they wanted.",
  },
  lethalTrifecta: {
    term: "Lethal trifecta",
    definition:
      "Private data, plus exposure to outside content, plus a way to send data out. An app with all three can be tricked into leaking data (Simon Willison, 2025).",
  },
  recordedRun: {
    term: "Recorded run",
    definition:
      "A real response from the model, saved earlier and played back so the demo works offline.",
  },
} as const satisfies Record<string, { term: string; definition: string }>;

export type GlossaryId = keyof typeof glossary;
