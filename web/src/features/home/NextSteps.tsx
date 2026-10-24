import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import type { EvalSummary } from "../../api/eval";
import { ofRuns, percent } from "../results/format";
import { useEvalSummary } from "../results/useEvalSummary";

function Row({ to, title, children }: { to: string; title: string; children: ReactNode }) {
  return (
    <li className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-1 px-6 py-4">
      <Link
        to={to}
        className="inline-flex items-center gap-1 text-body font-semibold text-accent underline-offset-4 hover:text-accent-hover hover:underline"
      >
        {title}
        <ChevronRight size={16} strokeWidth={1.75} aria-hidden="true" />
      </Link>
      <p className="max-w-prose text-small text-ink-2">{children}</p>
    </li>
  );
}

function Headline({ data }: { data: EvalSummary }) {
  const without = data.configs.find((c) => c.id === "A")?.attacks;
  const withLayer = data.configs.find((c) => c.id === "B")?.attacks;
  if (!without || !withLayer) return <>Attack success, false alarms and added time, measured.</>;
  return (
    <>
      Attacks worked in{" "}
      <span className="font-semibold text-ink tabular-nums">
        {percent(without.rate)} ({ofRuns(without)})
      </span>{" "}
      without SecuLayer and{" "}
      <span className="font-semibold text-ink tabular-nums">
        {percent(withLayer.rate)} ({ofRuns(withLayer)})
      </span>{" "}
      with it.
    </>
  );
}

/** Where to go after the demo: the explainer, the measured results and the limits. */
export function NextSteps() {
  const results = useEvalSummary();
  return (
    <ul className="divide-y divide-border rounded-card border border-border">
      <Row to="/how" title="How SecuLayer works">
        The five layers, what each one caught here, and how each one fails.
      </Row>
      <Row to="/results" title="Measured results">
        {results.status === "ok" ? (
          <Headline data={results.data} />
        ) : (
          "Attack success, false alarms and added time, measured on recorded runs."
        )}
      </Row>
      <Row to="/limits" title="What it can't stop">
        Prompt injection isn't solved. The attacks that still get through, and why.
      </Row>
    </ul>
  );
}
