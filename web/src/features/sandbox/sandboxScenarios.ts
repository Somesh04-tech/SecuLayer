import { setupOf, type CaseDetail, type ScenarioDetail } from "../../api/types";

export type SandboxScenarioId = "support" | "inbox" | "page" | "helpdesk";

export interface SandboxScenario {
  id: SandboxScenarioId;
  label: string;
  /** The attack whose attacker-controlled content the viewer edits. */
  baseCase: string;
  /** How /api/screen treats the text. */
  as: "user" | "outside";
  format: "text" | "html";
}

export const SANDBOX_SCENARIOS: readonly SandboxScenario[] = [
  {
    id: "support",
    label: "Support chat",
    baseCase: "support.override",
    as: "user",
    format: "text",
  },
  {
    id: "inbox",
    label: "Inbox assistant",
    baseCase: "inbox.hidden_forward",
    as: "outside",
    format: "html",
  },
  {
    id: "page",
    label: "Page summarizer",
    baseCase: "page.hidden_link",
    as: "outside",
    format: "html",
  },
  {
    id: "helpdesk",
    label: "HelpDesk",
    baseCase: "helpdesk.poisoned_phish",
    as: "outside",
    format: "text",
  },
];

export function sandboxScenario(id: string): SandboxScenario {
  return SANDBOX_SCENARIOS.find((s) => s.id === id) ?? SANDBOX_SCENARIOS[1]!;
}

export interface EditTarget {
  /** The attacker's content, as the app sends it to the model. */
  original: string;
  /** "You're the attacker: …" */
  role: string;
  /** What the editor holds, for its label. */
  what: string;
}

/** The base case's attacker-controlled content and how to describe it. */
export function editTarget(scenario: ScenarioDetail, caseDetail: CaseDetail): EditTarget {
  const setup = setupOf(caseDetail);
  switch (setup.kind) {
    case "chat":
      return {
        original: setup.message || caseDetail.user_request,
        role: "You're the attacker: you type straight into the store's chat. Edit the message the customer sends Fern.",
        what: "The customer's message",
      };
    case "inbox": {
      const email = setup.emails.find((e) => e.case_specific) ?? setup.emails[0];
      const sender = email ? email.from.split("<")[0]!.trim() : "a stranger";
      return {
        original: email?.body ?? "",
        role: `You're the attacker: edit the email ${sender} sends ${scenario.user_name}. The assistant reads it as raw HTML.`,
        what: `The email from ${sender} (HTML)`,
      };
    }
    case "page":
      return {
        original: setup.html,
        role: `You're the attacker: edit the web page ${scenario.user_name} opens. The summarizer reads its full HTML source, hidden parts included.`,
        what: "The page's HTML",
      };
    case "helpdesk": {
      const article = setup.articles.find((a) => a.case_specific) ?? setup.articles[0];
      return {
        original: article?.body ?? "",
        role: `You're the attacker: edit the wiki article “${article?.title ?? "an article"}”, which HelpDesk retrieves and reads as its own instructions.`,
        what: "The wiki article (plain text)",
      };
    }
  }
}
