import { Link } from "react-router";

import type { CaseResult, ConfigId, Coverage, LayerId } from "../../api/eval";
import { Chip, type ChipTone } from "../../components/Chip";

const COLUMNS: { id: LayerId; label: string }[] = [
  { id: "hidden_text", label: "Cleaner" },
  { id: "rules", label: "Rules" },
  { id: "classifier", label: "Classifier" },
  { id: "judge", label: "Judge" },
  { id: "tool_guard", label: "Tool guard" },
  { id: "output_guard", label: "Output guard" },
];

export const SYMBOL: Record<Coverage, { glyph: string; label: string }> = {
  all: { glyph: "●", label: "caught in every run" },
  some: { glyph: "◐", label: "caught in some runs" },
  none: { glyph: "○", label: "missed" },
  na: { glyph: "–", label: "doesn't apply" },
};

const SCENARIO_ORDER = ["support", "inbox", "page", "helpdesk"];

/** "Worked 3 of 3", "Stopped 3 of 3", "Paused 2 of 3"… for one configuration of one case. */
export function outcomeChip(
  result: CaseResult,
  config: ConfigId,
): { tone: ChipTone; text: string } {
  const runs = result.configs[config];
  if (!runs || runs.runs === 0) return { tone: "neutral", text: "Not run" };
  const of = `of ${runs.runs}`;
  if (runs.hits > 0) return { tone: "danger", text: `Worked ${runs.hits} ${of}` };
  if (runs.paused > 0) return { tone: "neutral", text: `Paused ${runs.paused} ${of}` };
  const stopped = runs.trials.filter((t) => t.outcome === "stopped").length;
  if (stopped > 0) return { tone: "safe", text: `Stopped ${stopped} ${of}` };
  return { tone: "neutral", text: `Resisted ${runs.runs} ${of}` };
}

export function primaryAttacks(cases: Record<string, CaseResult>): CaseResult[] {
  return Object.values(cases)
    .filter((c) => c.kind === "attack" && c.variant_of === null)
    .sort(
      (a, b) =>
        SCENARIO_ORDER.indexOf(a.scenario) - SCENARIO_ORDER.indexOf(b.scenario) ||
        a.id.localeCompare(b.id),
    );
}

/** Which layer caught which primary attack (§4.5): ● ◐ ○ – plus the outcomes both ways. */
export function CoverageMatrix({ cases }: { cases: Record<string, CaseResult> }) {
  const rows = primaryAttacks(cases);
  return (
    <div>
      <div
        className="max-h-[36rem] overflow-auto rounded-card border border-border"
        // A focusable scroll region, so keyboard users can scroll the table.
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
        tabIndex={0}
        role="region"
        aria-label="Which layer caught what (scrollable)"
      >
        <table className="w-full min-w-[56rem] border-separate border-spacing-0 text-small tabular-nums">
          <caption className="sr-only">Which layer caught which attack</caption>
          <thead>
            <tr className="text-ink-2">
              <th
                scope="col"
                className="sticky top-0 left-0 z-20 border-b border-border bg-surface-muted px-3 py-2 text-left font-semibold"
              >
                Attack
              </th>
              {COLUMNS.map((column) => (
                <th
                  key={column.id}
                  scope="col"
                  className="sticky top-0 z-10 border-b border-border bg-surface-muted px-3 py-2 text-center font-semibold"
                >
                  {column.label}
                </th>
              ))}
              <th
                scope="col"
                className="sticky top-0 z-10 border-b border-l border-border bg-surface-muted px-3 py-2 text-left font-semibold"
              >
                Without
              </th>
              <th
                scope="col"
                className="sticky top-0 z-10 border-b border-border bg-surface-muted px-3 py-2 text-left font-semibold"
              >
                With
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const without = outcomeChip(row, "A");
              const withLayer = outcomeChip(row, "B");
              return (
                <tr key={row.id} data-testid={`coverage-${row.id}`}>
                  <th
                    scope="row"
                    className="sticky left-0 z-10 border-b border-border bg-page px-3 py-2 text-left font-semibold"
                  >
                    <Link
                      to={`/lab/${row.scenario}?case=${encodeURIComponent(row.id)}`}
                      className="text-accent underline-offset-4 hover:text-accent-hover hover:underline"
                    >
                      {row.title}
                    </Link>
                  </th>
                  {COLUMNS.map((column) => {
                    const value = row.coverage?.[column.id] ?? "na";
                    const symbol = SYMBOL[value];
                    return (
                      <td
                        key={column.id}
                        className="border-b border-border px-3 py-2 text-center text-ink"
                      >
                        <span role="img" aria-label={`${column.label}: ${symbol.label}`}>
                          {symbol.glyph}
                        </span>
                      </td>
                    );
                  })}
                  <td className="border-b border-l border-border px-3 py-2">
                    <Chip tone={without.tone}>{without.text}</Chip>
                  </td>
                  <td className="border-b border-border px-3 py-2">
                    <Chip tone={withLayer.tone}>{withLayer.text}</Chip>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-small text-ink-3">
        {(["all", "some", "none", "na"] as const).map((key) => (
          <span key={key} className="mr-5 inline-block">
            <span aria-hidden="true" className="mr-1 text-ink">
              {SYMBOL[key].glyph}
            </span>
            {SYMBOL[key].label}
          </span>
        ))}
      </p>
      <p className="mt-1 max-w-prose text-small text-ink-3">
        Input-side columns come from SecuLayer watching the unprotected runs without changing
        anything (observe-only). Tool guard and output guard count the runs where the attack worked
        without SecuLayer: would that layer have stopped the harm?
      </p>
    </div>
  );
}
