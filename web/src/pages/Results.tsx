import { ChartColumn, ChevronRight, Download, RotateCw, TriangleAlert } from "lucide-react";
import { useEffect } from "react";
import { Link } from "react-router";

import type { EvalSummary } from "../api/eval";
import { Button, buttonClasses } from "../components/Button";
import { Code } from "../components/Code";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { Container } from "../components/Page";
import { Term } from "../components/Term";
import { CaseTables } from "../features/results/CaseTables";
import { CoverageMatrix } from "../features/results/CoverageMatrix";
import { day, ofRuns, shortModel } from "../features/results/format";
import { HowWeMeasured } from "../features/results/HowWeMeasured";
import { LayerTable } from "../features/results/LayerTable";
import { ResultsBarChart } from "../features/results/ResultsBarChart";
import { StatBlocks } from "../features/results/StatBlocks";
import { useEvalSummary } from "../features/results/useEvalSummary";

const LEAD =
  "Measured on recorded runs: how often attacks worked with and without SecuLayer, how often it blocked normal tasks, and how much time it added.";

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="mt-14">
      <h2 id={id} className="text-h2 text-ink">
        {title}
      </h2>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function Summary({ summary }: { summary: EvalSummary }) {
  const b = summary.configs.find((c) => c.id === "B");
  const caseTitle = (id: string | null) => (id ? summary.cases[id] : undefined);
  return (
    <>
      <p className="mt-3 text-small text-ink-2 tabular-nums">
        Measured {day(summary.recordings.last_recorded_at)} on{" "}
        <span className="font-mono text-mono">{summary.models.target}</span> ·{" "}
        {summary.dataset.attack_cases} attack cases and {summary.dataset.normal_cases} normal tasks,
        3 runs each ({shortModel(summary.models.compare)}: 1)
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-6">
        <a
          href="#how-we-measured"
          className="inline-flex items-center gap-1 text-small font-semibold text-accent underline-offset-4 hover:text-accent-hover hover:underline"
        >
          How we measured
          <ChevronRight size={16} strokeWidth={1.75} aria-hidden="true" />
        </a>
        <a
          href="/api/eval/latest"
          download="seculayer-latest.json"
          className={buttonClasses({ variant: "secondary" })}
        >
          <Download size={16} strokeWidth={1.75} aria-hidden="true" />
          Download raw results
        </a>
      </div>

      <Section id="attacks-heading" title="Attacks that worked">
        <p className="mb-6 max-w-prose text-body text-ink-2">
          The <Term id="attackSuccessRate">attack success rate</Term> in each configuration: the
          share of attack runs in which the attacker got what they wanted.
        </p>
        <ResultsBarChart configs={summary.configs} />
        {b?.paused && b.attacks_if_approved && (
          <p className="mt-4 max-w-prose text-small text-ink-2 tabular-nums" data-testid="paused">
            With full SecuLayer, runs paused for Dana's approval: {ofRuns(b.paused)}. If every
            confirmation had been approved: {ofRuns(b.attacks_if_approved)} would have worked.
          </p>
        )}
      </Section>

      <Section id="cost-heading" title="What it costs">
        <StatBlocks summary={summary} />
      </Section>

      <Section id="layers-heading" title="What each layer caught">
        <LayerTable layers={summary.layers} />
      </Section>

      <Section id="matrix-heading" title="Which layer caught what">
        <CoverageMatrix cases={summary.cases} />
        <div className="mt-8">
          <CaseTables cases={summary.cases} />
        </div>
      </Section>

      {summary.caveats.length > 0 && (
        <Section id="caveats-heading" title="Caveats">
          <ul className="max-w-prose space-y-3 text-body text-ink-2" data-testid="caveats">
            {summary.caveats.map((caveat, index) => {
              const result = caseTitle(caveat.case_id);
              return (
                <li key={index} className="flex gap-2">
                  <TriangleAlert
                    size={20}
                    strokeWidth={1.75}
                    aria-hidden="true"
                    className="mt-0.5 shrink-0 text-ink-3"
                  />
                  <span>
                    {result && (
                      <>
                        <Link
                          to={`/lab/${result.scenario}?case=${encodeURIComponent(result.variant_of ?? result.id)}`}
                          className="font-semibold text-accent underline-offset-4 hover:text-accent-hover hover:underline"
                        >
                          {result.title}
                        </Link>
                        :{" "}
                      </>
                    )}
                    {caveat.text}
                  </span>
                </li>
              );
            })}
          </ul>
        </Section>
      )}

      <section
        id="how-we-measured"
        aria-labelledby="how-heading"
        className="mt-14 scroll-mt-6 border-t border-border pt-10"
      >
        <h2 id="how-heading" className="text-h2 text-ink">
          How we measured
        </h2>
        <div className="mt-5">
          <HowWeMeasured summary={summary} />
        </div>
      </section>
    </>
  );
}

/** The evaluation numbers (§3.3, §7.5): every rate with its denominator. */
export function ResultsPage() {
  const state = useEvalSummary();
  useEffect(() => {
    document.title = "Results · SecuLayer";
  }, []);

  return (
    <Container className="py-12">
      <h1 className="text-h1 text-ink">Results</h1>
      <p className="mt-3 max-w-prose text-lead text-ink-2">{LEAD}</p>
      <div className="mt-6">
        {state.status === "loading" && (
          <p className="text-body text-ink-3" role="status">
            Loading the measured results…
          </p>
        )}
        {state.status === "missing" && (
          <EmptyState
            icon={ChartColumn}
            title="No results yet."
            help={
              <>
                Run <Code>make eval</Code> to measure them.
              </>
            }
          />
        )}
        {state.status === "error" && (
          <ErrorState
            icon={ChartColumn}
            title="Couldn't load the results."
            help={state.error.message}
            action={
              <Button variant="secondary" icon={RotateCw} onClick={state.retry}>
                Try again
              </Button>
            }
          />
        )}
        {state.status === "ok" && <Summary summary={state.data} />}
      </div>
    </Container>
  );
}
