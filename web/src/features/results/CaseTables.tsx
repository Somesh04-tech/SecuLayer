import { Link } from "react-router";

import type { CaseResult, ConfigId } from "../../api/eval";
import { Disclosure } from "../../components/Disclosure";

const SCENARIO_ORDER = ["support", "inbox", "page", "helpdesk"];

function ordered(cases: CaseResult[]): CaseResult[] {
  return [...cases].sort(
    (a, b) =>
      SCENARIO_ORDER.indexOf(a.scenario) - SCENARIO_ORDER.indexOf(b.scenario) ||
      a.id.localeCompare(b.id),
  );
}

function count(result: CaseResult, config: ConfigId): string {
  const runs = result.configs[config];
  if (!runs || runs.runs === 0) return "–";
  const paused = runs.paused > 0 ? ` (+${runs.paused} paused)` : "";
  return `${runs.hits} of ${runs.runs}${paused}`;
}

function CaseLink({ result }: { result: CaseResult }) {
  return (
    <Link
      to={`/lab/${result.scenario}?case=${encodeURIComponent(result.variant_of ?? result.id)}`}
      className="text-accent underline-offset-4 hover:text-accent-hover hover:underline"
    >
      {result.title}
    </Link>
  );
}

const cell = "px-3 py-1.5 align-top";
const head = "px-3 py-2 text-left font-semibold";

/** Every case's counts out of its trials (§7.3: "lists every case's count out of 3"). */
export function CaseTables({ cases }: { cases: Record<string, CaseResult> }) {
  const all = Object.values(cases);
  const attacks = ordered(all.filter((c) => c.kind === "attack"));
  const normal = ordered(all.filter((c) => c.kind === "normal"));
  return (
    <div className="space-y-4">
      <Disclosure title={`All ${attacks.length} attack cases`}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[44rem] text-small tabular-nums">
            <caption className="sr-only">
              Attack runs in which the attack worked, per case and configuration
            </caption>
            <thead>
              <tr className="bg-surface-muted text-ink-2">
                <th scope="col" className={head}>
                  Case
                </th>
                <th scope="col" className={head}>
                  Without (A)
                </th>
                <th scope="col" className={head}>
                  Full SecuLayer (B)
                </th>
                <th scope="col" className={head}>
                  gpt-5.4 (C)
                </th>
                <th scope="col" className={head}>
                  Hardening only (D)
                </th>
              </tr>
            </thead>
            <tbody>
              {attacks.map((result) => (
                <tr key={result.id} className="border-t border-border">
                  <th scope="row" className={`${cell} text-left font-normal`}>
                    <CaseLink result={result} />
                    {result.variant_of && <span className="block text-ink-3">Variant</span>}
                  </th>
                  <td className={cell}>{count(result, "A")}</td>
                  <td className={cell}>{count(result, "B")}</td>
                  <td className={cell}>{count(result, "C")}</td>
                  <td className={cell}>{count(result, "D")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Disclosure>
      <Disclosure title={`All ${normal.length} normal-use cases`}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-small tabular-nums">
            <caption className="sr-only">Normal-use runs done right, and false alarms</caption>
            <thead>
              <tr className="bg-surface-muted text-ink-2">
                <th scope="col" className={head}>
                  Case
                </th>
                <th scope="col" className={head}>
                  Done right without
                </th>
                <th scope="col" className={head}>
                  Done right with
                </th>
                <th scope="col" className={head}>
                  False alarms
                </th>
              </tr>
            </thead>
            <tbody>
              {normal.map((result) => (
                <tr key={result.id} className="border-t border-border">
                  <th scope="row" className={`${cell} text-left font-normal`}>
                    <CaseLink result={result} />
                  </th>
                  <td className={cell}>{count(result, "A")}</td>
                  <td className={cell}>{count(result, "B")}</td>
                  <td className={cell}>
                    {result.false_alarms ?? 0} of {result.configs.B?.runs ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Disclosure>
    </div>
  );
}
