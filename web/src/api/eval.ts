/**
 * The evaluation summary, data/eval/latest.json, served by GET /api/eval/latest
 * (docs/PLAN.md §7.3–7.5). Written by `make eval` (src/seculayer_demo/evaluation/).
 *
 * Every rate carries its denominator: `count` of `total`, plus an approximate 95% Wilson
 * score interval (trials of the same case aren't independent, so the interval is approximate).
 */

export interface Rate {
  count: number;
  total: number;
  /** count / total, 0–1; null when total is 0. */
  rate: number | null;
  /** 95% Wilson score interval, 0–1; null when total is 0. */
  ci: [number, number] | null;
}

export type ConfigId = "A" | "B" | "C" | "D" | "C+";

export interface ConfigResult {
  id: ConfigId;
  /** "Without SecuLayer", "Full SecuLayer", "Stronger model (gpt-5.4), no SecuLayer", … */
  label: string;
  model: string;
  protected: boolean;
  /** Plain-language scope, e.g. "all 56 cases × 3 trials". */
  scope: string;
  trials: number;
  /** Attack runs in which the attack's success check passed. Paused runs are not hits. */
  attacks: Rate | null;
  /** Attack runs that paused for confirmation (only B and C+). */
  paused: Rate | null;
  /** Hits if every confirmation had been approved. */
  attacks_if_approved: Rate | null;
  /** Normal-use runs whose utility check passed. Null where normal cases weren't run. */
  normal_done: Rate | null;
  /** Usage over this configuration's runs (app and judge calls). */
  usage: { input_tokens: number; output_tokens: number; calls: number; cost_usd: number };
}

export type LayerId =
  "hidden_text" | "rules" | "classifier" | "judge" | "hardening" | "tool_guard" | "output_guard";

export interface LayerResult {
  id: LayerId;
  label: string;
  /** input: share of attack runs where it would have intervened (observe-only over A).
   *  action: among A's successful attack runs where it applies, share where it would have
   *  stopped the harm. hardening: ASR(A) − ASR(D) on the 12 primary attacks. */
  kind: "input" | "action" | "hardening";
  caught: Rate | null;
  /** hardening only: ASR(A) and ASR(D) on the primary attacks, and their difference. */
  asr_without?: Rate;
  asr_hardening_only?: Rate;
  difference?: number | null;
  note: string;
}

/** ● caught in every run · ◐ in some · ○ missed · – doesn't apply */
export type Coverage = "all" | "some" | "none" | "na";

export interface TrialResult {
  trial: number;
  outcome:
    | "hijacked"
    | "resisted"
    | "stopped"
    | "paused"
    | "completed"
    | "false_alarm"
    | "failed"
    | "error";
  /** Attack success check (null for normal cases). */
  success: boolean | null;
  /** Utility check (null for attacks). */
  utility: boolean | null;
  stopped_by: string | null;
  /** For paused runs: would the attack have succeeded if Dana approved? */
  success_if_approved: boolean | null;
}

export interface CaseConfigResult {
  /** Attacks: success-check hits; normal cases: utility passes. */
  hits: number;
  runs: number;
  paused: number;
  trials: TrialResult[];
}

export interface CaseResult {
  id: string;
  title: string;
  scenario: string;
  kind: "attack" | "normal";
  variant_of: string | null;
  hard_case: boolean;
  configs: Partial<Record<ConfigId, CaseConfigResult>>;
  /** Attacks only: per-layer coverage from the observe-only pass and the action-side check. */
  coverage: Partial<Record<LayerId, Coverage>> | null;
  /** Normal cases only: false-alarm runs in B. */
  false_alarms: number | null;
}

export interface FalseAlarms {
  /** B's normal-use runs where SecuLayer did any of the four things below. */
  any: Rate;
  blocked: Rate;
  withheld: Rate;
  removed_needed: Rate;
  unneeded_confirmation: Rate;
}

export interface Distribution {
  median: number | null;
  p90: number | null;
  n: number;
}

export interface Caveat {
  case_id: string | null;
  text: string;
}

export interface EvalSummary {
  schema_version: 1;
  generated_at: string;
  models: { target: string; compare: string; judge: string };
  dataset: { attack_cases: number; primary_attacks: number; normal_cases: number };
  recordings: { count: number; first_recorded_at: string | null; last_recorded_at: string | null };
  configs: ConfigResult[];
  layers: LayerResult[];
  false_alarms: FalseAlarms;
  /** Per-run time difference B − A, from recorded model latencies plus SecuLayer's own
   *  recorded-free processing (excluded: see live). Milliseconds. */
  added_latency_ms: Distribution;
  /** Median ratio of B's app input tokens to A's, for runs that reached the model. */
  token_overhead: Distribution;
  cases: Record<string, CaseResult>;
  caveats: Caveat[];
  /** Measured live on this machine; the only part that changes between two `make eval` runs. */
  live: {
    layer_ms: Partial<
      Record<
        "hidden_text" | "screening" | "hardening" | "tool_guard" | "output_guard",
        Distribution
      >
    >;
    classifier: { available: boolean; cold_ms: number | null; cached_ms: number | null };
  };
}
