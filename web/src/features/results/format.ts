import type { CaseResult, ConfigId, Rate } from "../../api/eval";

/** 0.4722 → "47%" (whole percent; "<1%" for tiny non-zero rates). */
export function percent(rate: number | null): string {
  if (rate === null) return "–";
  if (rate > 0 && rate < 0.005) return "<1%";
  return `${Math.round(rate * 100)}%`;
}

/** "51 of 108 runs" */
export function ofRuns(rate: Rate, noun = "runs"): string {
  return `${rate.count} of ${rate.total} ${noun}`;
}

/** "gpt-5.4-mini-2026-03-17" → "gpt-5.4-mini" */
export function shortModel(snapshot: string): string {
  return snapshot.replace(/-\d{4}-\d{2}-\d{2}$/, "");
}

/** "2026-10-24T09:12:00Z" → "2026-10-24" */
export function day(timestamp: string | null): string {
  return timestamp ? timestamp.slice(0, 10) : "an unknown date";
}

/** "+0.4 s" from milliseconds. */
export function seconds(ms: number | null, sign = true): string {
  if (ms === null) return "–";
  const value = (ms / 1000).toFixed(1);
  return `${sign && ms >= 0 ? "+" : ""}${value} s`;
}

/** Bar labels in the order the wireframe reads (§3.3). */
export const CONFIG_ORDER: ConfigId[] = ["A", "D", "B", "C", "C+"];

export const CONFIG_LABEL: Record<ConfigId, string> = {
  A: "Without SecuLayer",
  D: "Prompt hardening only (12 attacks)",
  B: "Full SecuLayer",
  C: "Stronger model (gpt-5.4), no SecuLayer",
  "C+": "gpt-5.4 with full SecuLayer",
};

/** A scenario detail's `measured` entry for a case, typed. */
export function measuredCase(
  measured: Record<string, unknown> | null | undefined,
  caseId: string,
): CaseResult | null {
  const entry = measured?.[caseId];
  return entry && typeof entry === "object" ? (entry as CaseResult) : null;
}
