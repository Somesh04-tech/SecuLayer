import { ChevronRight, EyeOff } from "lucide-react";
import { clsx } from "clsx";
import { useId, useState } from "react";

import type { components } from "../../api/types.gen";
import { LAYER_LABELS, type LayerName, type VerdictAction } from "../../api/types";
import { VerdictChip } from "../lab/run/VerdictChip";

export type ScreenResult = components["schemas"]["ScreenResult"];
type VerdictOut = components["schemas"]["VerdictOut"];

function VerdictRow({ verdict, userName }: { verdict: VerdictOut; userName: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const lines = [
    ...verdict.detail,
    ...verdict.findings
      .map((f) => f.explanation)
      .filter((text) => !verdict.detail.some((line) => line.includes(text))),
  ];
  const unique = [...new Set(lines)].filter(Boolean);
  const name = LAYER_LABELS[verdict.layer as LayerName] ?? verdict.layer;
  return (
    <li className="py-3" data-layer={verdict.layer} data-action={verdict.action}>
      <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
        <span className="w-40 shrink-0 pt-0.5 text-small font-semibold text-ink">{name}</span>
        <VerdictChip action={verdict.action as VerdictAction} userName={userName} />
        <span className="ml-auto pt-0.5 text-caption text-ink-3 tabular-nums">
          {Math.round(verdict.latency_ms)} ms
        </span>
      </div>
      <p className="mt-1 text-small text-ink-2">{verdict.reason}</p>
      {unique.length > 0 && (
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
      )}
    </li>
  );
}

function summary(result: ScreenResult, asUser: boolean, userName: string): string {
  if (result.blocked) return "Screening would block your message before the model sees it.";
  if (result.withheld)
    return "Screening would withhold your text: the model would get a placeholder instead.";
  if (result.hidden.length > 0)
    return `The hidden-text cleaner would remove what ${userName} can't see. The rest reaches the model.`;
  return asUser
    ? "Your message would reach the model unchanged."
    : "Your text would reach the model; the later layers would still check what it makes the assistant do.";
}

/** Layers 1–2 on the viewer's own text (POST /api/screen). */
export function ScreenResultView({
  result,
  asUser,
  userName,
}: {
  result: ScreenResult;
  asUser: boolean;
  userName: string;
}) {
  return (
    <div className="space-y-6" data-testid="screen-result">
      <p className="text-body text-ink">{summary(result, asUser, userName)}</p>
      <div>
        <h3 className="text-small font-semibold text-ink">How SecuLayer decided</h3>
        <ul className="mt-1 divide-y divide-border">
          {result.verdicts.map((verdict) => (
            <VerdictRow key={verdict.layer} verdict={verdict} userName={userName} />
          ))}
        </ul>
        <p className="mt-2 text-caption text-ink-3">
          The LLM judge is off here: it needs a model call. Prompt hardening, the tool guard and the
          output guard act on the model's request and reply, so they need live mode.
        </p>
      </div>
      {result.hidden.length > 0 && (
        <div>
          <h3 className="flex items-center gap-1.5 text-small font-semibold text-ink">
            <EyeOff size={16} strokeWidth={1.75} aria-hidden="true" />
            Hidden text removed
          </h3>
          <ul className="mt-2 space-y-2">
            {result.hidden.map((piece, index) => (
              <li key={index} className="text-small">
                <span className="text-ink-3">{piece.reason}: </span>
                <span className="font-mono text-mono break-words text-danger-ink">
                  {piece.text || "(invisible characters)"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div>
        <h3 className="text-small font-semibold text-ink">
          {result.blocked
            ? "What the message would have been (screening stops it before the model)"
            : result.withheld
              ? "What the model would read instead"
              : "What the model would read"}
        </h3>
        <pre className="mt-2 max-h-72 overflow-auto rounded-control bg-surface-muted px-4 py-3 font-mono text-mono break-words whitespace-pre-wrap text-ink">
          {result.cleaned_text || "(nothing)"}
        </pre>
      </div>
    </div>
  );
}
