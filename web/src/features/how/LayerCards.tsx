import { ChevronRight } from "lucide-react";
import { Link } from "react-router";

import type { LayerResult } from "../../api/eval";
import { Code } from "../../components/Code";
import { ofRuns, percent } from "../results/format";
import { useEvalSummary, type EvalState } from "../results/useEvalSummary";
import { LAYER_GUIDES, type LayerGuide } from "./content";

function Measured({ guide, state }: { guide: LayerGuide; state: EvalState }) {
  if (state.status === "loading") {
    return <p className="text-small text-ink-3">Loading the measured results…</p>;
  }
  if (state.status === "missing") {
    return (
      <p className="text-small text-ink-2">
        Not measured yet. Run <Code>make eval</Code> to measure it.
      </p>
    );
  }
  if (state.status === "error") {
    return <p className="text-small text-ink-2">The measured results couldn't be loaded.</p>;
  }
  const results = guide.measures
    .map((id) => state.data.layers.find((layer) => layer.id === id))
    .filter((layer): layer is LayerResult => layer !== undefined);
  if (results.length === 0) {
    return <p className="text-small text-ink-2">This build's results don't measure it.</p>;
  }
  return (
    <ul className="space-y-2 text-small text-ink-2">
      {results.map((layer) => (
        <li key={layer.id}>
          <MeasuredLine layer={layer} />
        </li>
      ))}
    </ul>
  );
}

function MeasuredLine({ layer }: { layer: LayerResult }) {
  if (layer.kind === "hardening" && layer.asr_without && layer.asr_hardening_only) {
    return (
      <>
        On the 12 primary attacks, attacks worked in{" "}
        <span className="font-semibold text-ink tabular-nums">{ofRuns(layer.asr_without)}</span>{" "}
        without SecuLayer and in{" "}
        <span className="font-semibold text-ink tabular-nums">
          {ofRuns(layer.asr_hardening_only)}
        </span>{" "}
        with prompt hardening alone.
      </>
    );
  }
  if (!layer.caught) return <>{layer.note}</>;
  const name = layer.label.replace(/^Screening: /, "");
  return (
    <>
      {layer.id === "rules" || layer.id === "classifier" || layer.id === "judge" ? (
        <span className="font-semibold text-ink">{name[0]?.toUpperCase() + name.slice(1)}: </span>
      ) : null}
      <span className="font-semibold text-ink tabular-nums">
        {percent(layer.caught.rate)} ({ofRuns(layer.caught)})
      </span>
      <span className="block text-ink-3">{layer.note}</span>
    </>
  );
}

/** One card per layer: what it does, what it caught here, how it fails (§3.3). */
export function LayerCards() {
  const state = useEvalSummary();
  return (
    <ol className="space-y-6">
      {LAYER_GUIDES.map((guide) => (
        <li key={guide.id}>
          <article
            aria-labelledby={`layer-${guide.id}`}
            className="rounded-card border border-border p-6"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
              <h3 id={`layer-${guide.id}`} className="text-h3 text-ink">
                <span className="text-ink-3">Layer {guide.n} · </span>
                {guide.name}
              </h3>
              <Link
                to={guide.demo.to}
                className="inline-flex items-center gap-1 text-small font-semibold text-accent underline-offset-4 hover:text-accent-hover hover:underline"
              >
                See it in the demo: {guide.demo.label}
                <ChevronRight size={16} strokeWidth={1.75} aria-hidden="true" />
              </Link>
            </div>
            <div className="mt-4 grid gap-8 lg:grid-cols-3">
              <section>
                <h4 className="text-small font-semibold text-ink">What it does</h4>
                <p className="mt-1 text-small text-ink-2">{guide.does}</p>
              </section>
              <section>
                <h4 className="text-small font-semibold text-ink">What it caught in this demo</h4>
                <div className="mt-1">
                  <Measured guide={guide} state={state} />
                </div>
              </section>
              <section>
                <h4 className="text-small font-semibold text-ink">How it fails</h4>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-small text-ink-2">
                  {guide.fails.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </section>
            </div>
          </article>
        </li>
      ))}
    </ol>
  );
}
