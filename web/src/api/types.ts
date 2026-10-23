/**
 * Friendly names for the generated API types (types.gen.ts, from `make types`), plus the
 * per-app setup shapes, which the API sends as free-form objects.
 */
import type { components } from "./types.gen";

type S = components["schemas"];

export type ScenarioSummary = S["ScenarioSummary"];
export type ScenarioDetail = S["ScenarioDetail"];
export type CaseDetail = S["CaseDetail"];

export type RunStarted = S["RunStarted"];
export type LayerStarted = S["LayerStarted"];
export type LayerVerdict = S["LayerVerdict"];
export type ModelRequest = S["ModelRequest"];
export type ModelResponse = S["ModelResponse"];
export type ToolProposed = S["ToolProposed"];
export type ToolDecision = S["ToolDecision"];
export type RunPaused = S["RunPaused"];
export type ToolResult = S["ToolResult"];
export type AttackerEvent = S["AttackerEvent"];
export type RunFinished = S["RunFinished"];
export type RunError = S["RunError"];
export type RunEvent =
  | RunStarted
  | LayerStarted
  | LayerVerdict
  | ModelRequest
  | ModelResponse
  | ToolProposed
  | ToolDecision
  | RunPaused
  | ToolResult
  | AttackerEvent
  | RunFinished
  | RunError;

export type Finding = S["FindingOut"];
export type Dialog = S["Dialog"];
export type ActionOut = S["ActionOut"];
export type Outcome = RunFinished["outcome"];
export type LayerName = LayerVerdict["layer"];
export type VerdictAction = LayerVerdict["action"];
export type AnatomyMessage = S["AnatomyMessage"];
export type AnatomyPart = S["AnatomyPart"];

export const LAYERS: readonly LayerName[] = [
  "hidden_text",
  "screening",
  "hardening",
  "tool_guard",
  "output_guard",
];

/** The layer names used everywhere in the UI (§3.5). */
export const LAYER_LABELS: Record<LayerName, string> = {
  hidden_text: "Hidden-text cleaner",
  screening: "Screening",
  hardening: "Prompt hardening",
  tool_guard: "Tool guard",
  output_guard: "Output guard",
};

/** One piece of what the model reads of an outside item ("Show what the AI reads"). */
export interface ReadPart {
  text: string;
  source: "developer" | "user" | "external" | "injected" | "seculayer" | "model";
  hidden: boolean;
  hidden_kind: "css" | "comment" | "tag_chars" | "zero_width" | null;
}

export interface SetupEmail {
  id: string;
  from: string;
  subject: string;
  received: string;
  body: string;
  format: "html" | "text";
  private: boolean;
  outside: boolean;
  /** The case's fifth email (the attacker's, in attack cases). */
  case_specific: boolean;
  reads: ReadPart[];
}

export interface SetupArticle {
  id: string;
  title: string;
  author: string;
  edited: string;
  verified: boolean;
  body: string;
  case_specific: boolean;
  reads: ReadPart[];
}

export type Setup =
  | { kind: "chat"; message: string; reads: ReadPart[] }
  | { kind: "inbox"; emails: SetupEmail[] }
  | { kind: "page"; url: string; html: string; title: string; notes: string; reads: ReadPart[] }
  | { kind: "helpdesk"; question: string; articles: SetupArticle[] };

export function setupOf(detail: CaseDetail): Setup {
  return detail.setup as unknown as Setup;
}

export interface RunBody {
  case_id: string;
  protected: boolean;
  layers?: Partial<Record<string, boolean>>;
  model?: string;
  trial?: number;
}
