import { clsx } from "clsx";

import type { ConfigResult } from "../../api/eval";
import { Disclosure } from "../../components/Disclosure";
import { CONFIG_LABEL, CONFIG_ORDER, ofRuns, percent } from "./format";

const TRACK_HEIGHT = 20;
const BAR_HEIGHT = 12;

/**
 * Attack success rate by configuration (§4.5): one thin horizontal bar per configuration,
 * a whisker for the approximate 95% Wilson interval, and direct labels. No legend, no grid.
 * "Attack worked" bars use danger-solid; the full-SecuLayer bar uses safe-solid.
 */
export function ResultsBarChart({ configs }: { configs: ConfigResult[] }) {
  const rows = CONFIG_ORDER.map((id) => configs.find((c) => c.id === id)).filter(
    (c): c is ConfigResult => c !== undefined && c.attacks !== null,
  );
  return (
    <figure className="max-w-4xl" aria-labelledby="attacks-chart-caption">
      <ul className="space-y-3">
        {rows.map((config) => {
          const rate = config.attacks!;
          const value = rate.rate ?? 0;
          const [low, high] = rate.ci ?? [value, value];
          const safe = config.id === "B" || config.id === "C+";
          return (
            <li
              key={config.id}
              data-testid={`bar-${config.id}`}
              className="grid grid-cols-[minmax(0,15rem)_minmax(0,1fr)_7.5rem] items-center gap-4 text-small lg:grid-cols-[minmax(0,18rem)_minmax(0,1fr)_9rem]"
            >
              <span className="text-ink">{CONFIG_LABEL[config.id] ?? config.label}</span>
              <svg
                aria-hidden="true"
                className="h-5 w-full overflow-visible"
                viewBox={`0 0 100 ${TRACK_HEIGHT}`}
                preserveAspectRatio="none"
              >
                <title>{`${config.label}: ${percent(rate.rate)} (${ofRuns(rate)})`}</title>
                <rect
                  x={0}
                  y={(TRACK_HEIGHT - BAR_HEIGHT) / 2}
                  width={Math.max(value * 100, value > 0 ? 0.6 : 0)}
                  height={BAR_HEIGHT}
                  className={safe ? "fill-safe-solid" : "fill-danger-solid"}
                />
                {rate.ci && (
                  <g data-testid={`whisker-${config.id}`} className="stroke-ink">
                    <line
                      x1={low * 100}
                      x2={high * 100}
                      y1={TRACK_HEIGHT / 2}
                      y2={TRACK_HEIGHT / 2}
                      strokeWidth={1.5}
                      vectorEffect="non-scaling-stroke"
                    />
                    {[low, high].map((end, i) => (
                      <line
                        key={i}
                        x1={end * 100}
                        x2={end * 100}
                        y1={3}
                        y2={TRACK_HEIGHT - 3}
                        strokeWidth={1.5}
                        vectorEffect="non-scaling-stroke"
                      />
                    ))}
                  </g>
                )}
              </svg>
              <span className="tabular-nums">
                <span className={clsx("font-semibold", safe ? "text-safe-ink" : "text-ink")}>
                  {percent(rate.rate)}
                </span>{" "}
                <span className="text-ink-3">{ofRuns(rate)}</span>
              </span>
            </li>
          );
        })}
      </ul>
      <figcaption id="attacks-chart-caption" className="mt-4 text-small text-ink-3">
        Bars show the share of attack runs in which the attack worked; whiskers show the approximate
        95% confidence interval.
      </figcaption>
      <Disclosure title="Show as a table" className="mt-3">
        <table className="text-small tabular-nums">
          <caption className="sr-only">Attacks that worked, by configuration</caption>
          <thead>
            <tr className="text-left text-ink-3">
              <th scope="col" className="py-1 pr-6 font-semibold">
                Configuration
              </th>
              <th scope="col" className="py-1 pr-6 font-semibold">
                Attacks that worked
              </th>
              <th scope="col" className="py-1 font-semibold">
                95% interval
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((config) => (
              <tr key={config.id} className="border-t border-border">
                <th scope="row" className="py-1 pr-6 text-left font-normal text-ink">
                  {CONFIG_LABEL[config.id] ?? config.label}
                </th>
                <td className="py-1 pr-6">
                  {percent(config.attacks!.rate)} ({ofRuns(config.attacks!)})
                </td>
                <td className="py-1">
                  {config.attacks!.ci
                    ? `${percent(config.attacks!.ci[0])}–${percent(config.attacks!.ci[1])}`
                    : "–"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Disclosure>
    </figure>
  );
}
