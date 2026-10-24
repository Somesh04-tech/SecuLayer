import type { LayerResult } from "../../api/eval";
import { ofRuns, percent } from "./format";

const KIND: Record<LayerResult["kind"], string> = {
  input: "Would have intervened, out of attack runs",
  action: "Would have stopped the harm, out of attack runs that worked without SecuLayer",
  hardening: "Attack success rate without SecuLayer minus with prompt hardening alone",
};

function points(difference: number | null | undefined): string {
  if (difference === null || difference === undefined) return "–";
  const value = Math.round(difference * 100);
  return `${value > 0 ? "−" : value < 0 ? "+" : ""}${Math.abs(value)} points`;
}

/** What each layer caught, measured in observe-only mode over the unprotected runs (§7.3). */
export function LayerTable({ layers }: { layers: LayerResult[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] text-small tabular-nums">
        <caption className="sr-only">What each layer caught</caption>
        <thead>
          <tr className="bg-surface-muted text-left text-ink-2">
            <th scope="col" className="px-3 py-2 font-semibold">
              Layer
            </th>
            <th scope="col" className="px-3 py-2 font-semibold">
              Measured
            </th>
            <th scope="col" className="px-3 py-2 font-semibold">
              What it means
            </th>
          </tr>
        </thead>
        <tbody>
          {layers.map((layer) => (
            <tr key={layer.id} data-testid={`layer-${layer.id}`} className="border-t border-border">
              <th scope="row" className="px-3 py-2 text-left align-top font-semibold text-ink">
                {layer.label}
              </th>
              <td className="px-3 py-2 align-top whitespace-nowrap text-ink">
                {layer.kind === "hardening" ? (
                  <>
                    {points(layer.difference)}
                    {layer.asr_without && layer.asr_hardening_only && (
                      <span className="block text-ink-3">
                        {ofRuns(layer.asr_without)} → {ofRuns(layer.asr_hardening_only)}
                      </span>
                    )}
                  </>
                ) : layer.caught ? (
                  <>
                    {percent(layer.caught.rate)}{" "}
                    <span className="text-ink-3">({ofRuns(layer.caught)})</span>
                  </>
                ) : (
                  "–"
                )}
              </td>
              <td className="px-3 py-2 align-top text-ink-2">
                <span className="block">{KIND[layer.kind]}.</span>
                {layer.note && <span className="mt-1 block text-ink-3">{layer.note}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
