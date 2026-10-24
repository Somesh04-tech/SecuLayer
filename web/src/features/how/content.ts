import type { LayerId } from "../../api/eval";

export interface LayerGuide {
  id: "hidden_text" | "screening" | "hardening" | "tool_guard" | "output_guard";
  n: number;
  name: string;
  does: string;
  fails: string[];
  demo: { to: string; label: string };
  /** Entries of the evaluation's `layers` array that measure this layer. */
  measures: LayerId[];
}

/** Each layer in plain language (docs/PLAN.md §6.2). */
export const LAYER_GUIDES: LayerGuide[] = [
  {
    id: "hidden_text",
    n: 1,
    name: "Hidden-text cleaner",
    does: "Makes outside content look to the model the way it looks to a person. It removes text a browser wouldn't show (white or tiny text, hidden elements, HTML comments) and invisible Unicode characters, and decodes invisible tag characters so you can read what they said.",
    fails: [
      "Hidden text the browser would only hide with an external stylesheet, a complex selector or a transform gets through.",
      "Visible injected text passes untouched.",
      "It can remove legitimate hidden text, such as an email preheader.",
    ],
    demo: { to: "/lab/inbox?case=inbox.hidden_forward", label: "The invisible footer" },
    measures: ["hidden_text"],
  },
  {
    id: "screening",
    n: 2,
    name: "Screening",
    does: "Checks the user's message and every piece of outside content for text that tries to instruct the AI. Rules look for known phrasings, a small classifier scores the text, and an LLM judge reads it. A blocked user message stops the run; a flagged email, page or article is withheld from the model.",
    fails: [
      "Rules are brittle: paraphrases, typos and other languages slip past, and normal text can trip them.",
      "The classifier catches blunt attack wording but misses requests that only make sense in context.",
      "The judge costs a model call and can itself be addressed by the attacker's text.",
    ],
    demo: { to: "/lab/helpdesk?case=helpdesk.poisoned_phish", label: "The edited wiki page" },
    measures: ["rules", "classifier", "judge"],
  },
  {
    id: "hardening",
    n: 3,
    name: "Prompt hardening",
    does: "Moves outside content to the lowest-trust place in the prompt, wraps each item in markers with a random ID, replaces its spaces with a mark (spotlighting), and adds a short trust policy telling the model that outside content is data, not instructions.",
    fails: [
      "It lowers the chance the model follows injected text but doesn't remove it.",
      "A request that fits the user's own task can still be followed.",
      "The markers are plain text; an attacker who learned the ID could imitate them.",
    ],
    demo: { to: "/lab/support?case=support.roleplay", label: "The manager's last day" },
    measures: ["hardening"],
  },
  {
    id: "tool_guard",
    n: 4,
    name: "Tool guard",
    does: "Checks every tool call the model proposes before it runs. A send is allowed only if the user's own message asked for one; new recipients, addresses that came from outside content and private data going to strangers make SecuLayer ask the user first.",
    fails: [
      "It only checks the tools its policy marks as sensitive.",
      "People approve convincing requests: confirmation fatigue.",
      "Matching by text misses values the model rewords, and harm that needs no tool, such as a false fact, is out of its reach.",
    ],
    demo: { to: "/lab/inbox?case=inbox.polite_invoice", label: "The polite invoice" },
    measures: ["tool_guard"],
  },
  {
    id: "output_guard",
    n: 5,
    name: "Output guard",
    does: "Checks the final reply before it is shown. It withholds a reply that repeats the canary or a protected secret, removes images from outside domains (they load without a click), and neutralises links to domains the user never saw.",
    fails: [
      "It only finds what it is told to look for.",
      "Encodings it doesn't decode, such as a riddle or a translation, slip through.",
      "Allowlisted domains can host attacker content, and it can't recognise a false fact.",
    ],
    demo: { to: "/lab/page?case=page.image_exfil", label: "The tracking pixel" },
    measures: ["output_guard"],
  },
];
