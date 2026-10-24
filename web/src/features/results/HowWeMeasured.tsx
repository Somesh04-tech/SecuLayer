import type { EvalSummary } from "../../api/eval";
import { shortModel } from "./format";

const PURPOSE: Record<string, string> = {
  A: "The baseline: how often the unprotected app is hijacked.",
  B: "The protected result: every layer on, judge on.",
  C: "Model robustness: does a stronger model resist on its own?",
  D: "What placing and marking outside content achieves without any gate.",
  "C+": "The stronger model with SecuLayer on top.",
};

const LAYER_NAMES: Record<string, string> = {
  hidden_text: "Hidden-text cleaner",
  screening: "Screening",
  hardening: "Prompt hardening",
  tool_guard: "Tool guard",
  output_guard: "Output guard",
};

function ms(value: number | null): string {
  if (value === null) return "–";
  return value < 10 ? `${value.toFixed(1)} ms` : `${Math.round(value)} ms`;
}

/** §7.2–7.3 condensed, plus what was measured live on this machine. */
export function HowWeMeasured({ summary }: { summary: EvalSummary }) {
  const { classifier, layer_ms: layerMs } = summary.live;
  return (
    <div className="max-w-prose space-y-4 text-body text-ink-2">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] text-small">
          <caption className="sr-only">Configurations</caption>
          <thead>
            <tr className="bg-surface-muted text-left text-ink-2">
              <th scope="col" className="px-3 py-2 font-semibold">
                Configuration
              </th>
              <th scope="col" className="px-3 py-2 font-semibold">
                Model
              </th>
              <th scope="col" className="px-3 py-2 font-semibold">
                Cases × trials
              </th>
              <th scope="col" className="px-3 py-2 font-semibold">
                Purpose
              </th>
            </tr>
          </thead>
          <tbody>
            {summary.configs.map((config) => (
              <tr key={config.id} className="border-t border-border">
                <th scope="row" className="px-3 py-2 text-left align-top font-semibold text-ink">
                  {config.id} · {config.label}
                </th>
                <td className="px-3 py-2 align-top font-mono text-mono text-ink">
                  {shortModel(config.model)}
                </td>
                <td className="px-3 py-2 align-top">{config.scope}</td>
                <td className="px-3 py-2 align-top">{PURPOSE[config.id] ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        Every number comes from recorded real runs of {shortModel(summary.models.target)}, played
        back offline; the evaluation itself makes no model calls. An attack run counts as a hit when
        its success check passes: deterministic keyword, link and tool-call checks written before
        the runs. They are approximate by nature; the caveats above list where they over-count.
      </p>
      <p>
        A run that paused for Dana's approval counts as paused, not as a hit, because a person
        decides. The report also shows the rate if every confirmation had been approved.
      </p>
      <p>
        Per-layer rates come from observe-only mode: SecuLayer watches the unprotected runs,
        computes every layer's verdict and changes nothing. Prompt hardening is measured instead as
        the difference between the unprotected runs and runs with hardening alone.
      </p>
      <p>
        Intervals are 95% Wilson score intervals. Trials of the same case aren't independent, so
        treat them as approximate.
      </p>
      <p>
        Our attacks were written against the unprotected app. An attacker who studies SecuLayer does
        better: researchers broke 12 published defenses that way (Nasr et al., 2025). The screening
        rules were also written knowing these attacks; the variants and the normal-use bait measure
        how much that flatters them.
      </p>
      <section aria-labelledby="live-heading">
        <h3 id="live-heading" className="text-h3 text-ink">
          Measured live on this computer
        </h3>
        <ul className="mt-2 space-y-1 text-small tabular-nums">
          {Object.entries(layerMs).map(([layer, dist]) => (
            <li key={layer} className="flex justify-between gap-4">
              <span>{LAYER_NAMES[layer] ?? layer}, median processing time</span>
              <span>
                {ms(dist?.median ?? null)} ({dist?.n ?? 0} runs)
              </span>
            </li>
          ))}
          <li className="flex justify-between gap-4">
            <span>Classifier, one new text and one cached text</span>
            <span>
              {classifier.available
                ? `${ms(classifier.cold_ms)} · ${ms(classifier.cached_ms)}`
                : "classifier not downloaded on this machine"}
            </span>
          </li>
        </ul>
      </section>
    </div>
  );
}
