import { clsx } from "clsx";
import { ChevronRight, LoaderCircle } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { useId, useState } from "react";

import { LAYERS, LAYER_LABELS, type LayerName, type LayerVerdict } from "../../../api/types";
import type { LayerRow as Row } from "../useRun";
import { VerdictChip } from "./VerdictChip";

function Detail({ verdict }: { verdict: LayerVerdict }) {
  const detail = verdict.detail ?? [];
  const lines = [
    ...detail,
    ...verdict.findings
      .map((f) => f.explanation)
      .filter((text) => !detail.some((line) => line.includes(text))),
  ];
  const unique = [...new Set(lines)].filter(Boolean);
  const [open, setOpen] = useState(false);
  const id = useId();
  if (unique.length === 0) return null;
  return (
    <div className="mt-1">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 text-caption text-accent hover:text-accent-hover"
      >
        <ChevronRight
          size={16}
          strokeWidth={1.75}
          aria-hidden="true"
          className={clsx(
            "transition-transform duration-(--duration-expand) ease-standard",
            open && "rotate-90",
          )}
        />
        Details
      </button>
      {open && (
        <ul id={id} className="mt-1 space-y-1 pl-5 text-small text-ink-2">
          {unique.map((line) => (
            <li key={line} className="list-disc break-words">
              {line}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function LayerRow({ layer, row, userName }: { layer: LayerName; row: Row; userName: string }) {
  const reduced = useReducedMotion();
  const name = LAYER_LABELS[layer];
  if (row.status !== "done") {
    return (
      <li className="flex items-center gap-3 py-2" data-layer={layer} data-status={row.status}>
        <span className="w-40 shrink-0 text-small font-semibold text-ink">{name}</span>
        {row.status === "running" ? (
          <span className="inline-flex items-center gap-1.5 text-small text-ink-3">
            <LoaderCircle
              size={16}
              strokeWidth={1.75}
              aria-hidden="true"
              className="animate-spin motion-reduce:animate-none"
            />
            Checking…
          </span>
        ) : (
          <span className="text-small text-ink-3" aria-label="Waiting">
            ·
          </span>
        )}
      </li>
    );
  }
  const { verdict } = row;
  return (
    <motion.li
      data-layer={layer}
      data-status="done"
      data-action={verdict.action}
      initial={reduced ? false : { opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduced ? 0 : 0.24, ease: [0.2, 0.7, 0.2, 1] }}
      className="py-2"
    >
      <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
        <span className="w-40 shrink-0 pt-0.5 text-small font-semibold text-ink">{name}</span>
        <VerdictChip action={verdict.action} userName={userName} />
        <span className="ml-auto pt-0.5 text-caption text-ink-3 tabular-nums">
          {Math.round(verdict.latency_ms)} ms
        </span>
      </div>
      <p className="mt-1 line-clamp-2 text-small text-ink-2">{verdict.reason}</p>
      <Detail verdict={verdict} />
    </motion.li>
  );
}

/** The five layers in order, each with its verdict, reason and time (§4.5). */
export function Pipeline({
  layers,
  verdicts,
  userName,
}: {
  layers: Record<LayerName, Row>;
  verdicts: LayerVerdict[];
  userName: string;
}) {
  const total = verdicts.reduce((sum, v) => sum + v.latency_ms, 0);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-small font-semibold text-ink">How SecuLayer decided</h3>
        {verdicts.length > 0 && (
          <span className="text-caption text-ink-3 tabular-nums">
            SecuLayer's checks: {Math.round(total)} ms
          </span>
        )}
      </div>
      <ul className="mt-1 divide-y divide-border">
        {LAYERS.map((layer) => (
          <LayerRow key={layer} layer={layer} row={layers[layer]} userName={userName} />
        ))}
      </ul>
    </div>
  );
}
