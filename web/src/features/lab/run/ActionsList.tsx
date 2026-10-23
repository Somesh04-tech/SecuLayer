import { clsx } from "clsx";
import { Wrench } from "lucide-react";

import type { ActionOut } from "../../../api/types";
import { Term } from "../../../components/Term";

const STATUS: Record<ActionOut["status"], { label: string; className: string }> = {
  done: { label: "Done", className: "border-border-strong text-ink-2" },
  blocked: { label: "Blocked", className: "border-ink bg-ink text-page" },
  awaiting_approval: {
    label: "Awaiting approval",
    className: "border-accent-subtle bg-accent-subtle text-accent",
  },
  declined: { label: "Declined", className: "border-dashed border-border text-ink-3" },
};

function list(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join(", ");
  return value == null ? "" : String(value);
}

function Arguments({ action }: { action: ActionOut }) {
  const args = action.arguments;
  if (action.name === "send_email") {
    const to = [list(args.to), list(args.cc), list(args.bcc)].filter(Boolean).join(", ");
    const bcc = list(args.bcc);
    return (
      <dl className="mt-1 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 text-small">
        <dt className="text-ink-3">To</dt>
        <dd className="font-mono text-mono break-all text-ink">{to || "nobody"}</dd>
        {bcc && (
          <>
            <dt className="text-ink-3">Bcc</dt>
            <dd className="font-mono text-mono break-all text-ink">{bcc}</dd>
          </>
        )}
        <dt className="text-ink-3">Subject</dt>
        <dd className="break-words text-ink">{list(args.subject) || "(none)"}</dd>
      </dl>
    );
  }
  const shown = Object.entries(args).filter(([, v]) => v !== null && v !== "");
  return (
    <p className="mt-1 font-mono text-mono break-all text-ink-2">
      {action.name}({shown.map(([k, v]) => `${k}: ${list(v)}`).join(", ")})
    </p>
  );
}

/** The tool calls the model asked for, and what happened to each (§4.5). */
export function ActionsList({ actions }: { actions: ActionOut[] }) {
  if (actions.length === 0) {
    return (
      <p className="text-small text-ink-2">
        <span className="font-semibold text-ink">Actions taken:</span> none
      </p>
    );
  }
  return (
    <div>
      <h3 className="text-small font-semibold text-ink">
        Actions taken <span className="font-normal text-ink-3">(</span>
        <Term id="toolCall">tool calls</Term>
        <span className="font-normal text-ink-3">)</span>
      </h3>
      <ul className="mt-2 space-y-3">
        {actions.map((action) => (
          <li key={action.call_id} className="flex items-start gap-2">
            <Wrench
              size={16}
              strokeWidth={1.75}
              aria-hidden="true"
              className="mt-1 shrink-0 text-ink-3"
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-mono text-ink">{action.name}</span>
                <span
                  className={clsx(
                    "inline-flex h-6 items-center rounded-chip border px-2 text-caption",
                    STATUS[action.status].className,
                  )}
                >
                  {STATUS[action.status].label}
                </span>
              </div>
              <Arguments action={action} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
