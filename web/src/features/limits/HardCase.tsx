import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import type { CaseResult, EvalSummary } from "../../api/eval";
import { ButtonLink } from "../../components/Button";
import { Chip } from "../../components/Chip";

/** "Without SecuLayer, it worked in 2 of 3 recorded runs. With SecuLayer, …" */
export function measuredSentences(result: CaseResult): string[] {
  const out: string[] = [];
  const a = result.configs.A;
  const b = result.configs.B;
  if (a) out.push(`Without SecuLayer, it worked in ${a.hits} of ${a.runs} recorded runs.`);
  if (b) {
    let line = `With SecuLayer, it worked in ${b.hits} of ${b.runs}`;
    if (b.paused > 0) {
      const approved = b.trials.filter(
        (t) => t.outcome === "paused" && t.success_if_approved,
      ).length;
      line += `, and ${b.paused} of ${b.runs} paused for Dana's approval. If she had approved, ${approved} of those ${b.paused} would have succeeded.`;
    } else {
      line += ".";
    }
    out.push(line);
  }
  return out;
}

export function HardCase({
  id,
  title,
  labLink,
  summary,
  children,
}: {
  id: string;
  title: string;
  labLink: string;
  summary: EvalSummary | null;
  children: ReactNode;
}) {
  const result = summary?.cases[id] ?? null;
  const caveats = summary?.caveats.filter((c) => c.case_id === id) ?? [];
  const headingId = `hard-${id.replace(/\W/g, "-")}`;
  return (
    <section
      aria-labelledby={headingId}
      className="rounded-card border border-border p-6"
      data-testid={`hard-case-${id}`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <h3 id={headingId} className="text-h3 text-ink">
          {title}
        </h3>
        <Chip tone="strong">Hard case</Chip>
      </div>
      <div className="mt-3 max-w-prose space-y-3 text-body text-ink-2">{children}</div>
      <div className="mt-4 max-w-prose border-t border-border pt-4">
        <p className="text-small font-semibold text-ink">Measured</p>
        {result ? (
          <ul className="mt-1 space-y-1 text-body text-ink tabular-nums">
            {measuredSentences(result).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-body text-ink-2">
            Not measured yet. Run <code className="font-mono text-mono">make eval</code> to measure
            them.
          </p>
        )}
        {caveats.map((caveat) => (
          <p key={caveat.text} className="mt-2 text-small text-ink-3">
            {caveat.text}
          </p>
        ))}
      </div>
      <div className="mt-4">
        <ButtonLink to={labLink} variant="ghost" trailingIcon={ChevronRight}>
          Open in the demo
        </ButtonLink>
      </div>
    </section>
  );
}
