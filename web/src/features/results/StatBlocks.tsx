import type { EvalSummary, Rate } from "../../api/eval";
import { Term } from "../../components/Term";
import { ofRuns, percent, seconds } from "./format";

function Block({ title, children }: { title: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="border-t border-border pt-4">
      <h3 className="text-small font-semibold text-ink-2">{title}</h3>
      <div className="mt-2 tabular-nums">{children}</div>
    </section>
  );
}

function Figure({ value, detail }: { value: string; detail: string }) {
  return (
    <p>
      <span className="text-h2 text-ink">{value}</span>{" "}
      <span className="text-small text-ink-3">({detail})</span>
    </p>
  );
}

function TypeRow({ label, rate }: { label: string; rate: Rate }) {
  return (
    <li className="flex justify-between gap-4">
      <span>{label}</span>
      <span>{ofRuns(rate)}</span>
    </li>
  );
}

/** False alarms, task success and added time (§7.3), with their denominators. */
export function StatBlocks({ summary }: { summary: EvalSummary }) {
  const a = summary.configs.find((c) => c.id === "A");
  const b = summary.configs.find((c) => c.id === "B");
  const alarms = summary.false_alarms;
  return (
    <div className="grid gap-8 lg:grid-cols-3">
      <Block
        title={
          <>
            Normal tasks wrongly blocked (<Term id="falseAlarm">false alarms</Term>)
          </>
        }
      >
        <Figure value={percent(alarms.any.rate)} detail={ofRuns(alarms.any)} />
        <ul className="mt-3 space-y-1 text-small text-ink-2">
          <TypeRow label="Blocked the request" rate={alarms.blocked} />
          <TypeRow label="Withheld an item" rate={alarms.withheld} />
          <TypeRow label="Removed a needed link or image" rate={alarms.removed_needed} />
          <TypeRow label="Asked when it didn't need to" rate={alarms.unneeded_confirmation} />
        </ul>
      </Block>
      <Block title="Normal tasks done right">
        {a?.normal_done && b?.normal_done ? (
          <>
            <p>
              <span className="text-h2 text-ink">{percent(a.normal_done.rate)}</span>{" "}
              <span className="text-small text-ink-3">without</span>
              <span className="text-ink-3"> · </span>
              <span className="text-h2 text-ink">{percent(b.normal_done.rate)}</span>{" "}
              <span className="text-small text-ink-3">with</span>
            </p>
            <ul className="mt-3 space-y-1 text-small text-ink-2">
              <TypeRow label="Without SecuLayer" rate={a.normal_done} />
              <TypeRow label="With SecuLayer" rate={b.normal_done} />
            </ul>
          </>
        ) : (
          <p className="text-small text-ink-3">Not measured.</p>
        )}
      </Block>
      <Block title="Added time per run">
        <Figure
          value={`${seconds(summary.added_latency_ms.median)} median`}
          detail={`${summary.added_latency_ms.n} paired runs`}
        />
        <ul className="mt-3 space-y-1 text-small text-ink-2">
          <li className="flex justify-between gap-4">
            <span>90th percentile</span>
            <span>{seconds(summary.added_latency_ms.p90)}</span>
          </li>
          <li className="flex justify-between gap-4">
            <span>Input tokens, with ÷ without (median)</span>
            <span>
              {summary.token_overhead.median === null
                ? "–"
                : `×${summary.token_overhead.median.toFixed(2)}`}
            </span>
          </li>
        </ul>
      </Block>
    </div>
  );
}
