import { Hand } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

import type { Dialog as DialogData } from "../../../api/types";
import { Button } from "../../../components/Button";
import { Dialog } from "../../../components/Dialog";

/** Splits `text` and marks every highlight (case-insensitive) with the danger tokens. */
function highlight(text: string, needles: string[]): ReactNode[] {
  const wanted = needles.filter((n) => n.trim().length > 0);
  if (wanted.length === 0) return [text];
  const escaped = wanted.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "gi"));
  return parts.map((part, index) =>
    index % 2 === 1 ? (
      <mark key={index} className="rounded-chip bg-danger-bg px-0.5 text-danger-ink">
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

/**
 * SecuLayer paused an action (§3.3): what the assistant wants to send, why the tool guard
 * asked, and the user's choice. "Don't send" has focus; Escape or the overlay also means
 * "Don't send".
 */
export function ConfirmDialog({
  open,
  dialog,
  userName,
  onDecide,
}: {
  open: boolean;
  dialog: DialogData;
  userName: string;
  onDecide: (approve: boolean) => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const decided = useRef(false);
  useEffect(() => {
    if (open) decided.current = false;
  }, [open]);
  const decide = (approve: boolean) => {
    if (decided.current) return;
    decided.current = true;
    onDecide(approve);
  };
  const needles = dialog.highlights.map((h) => h.text);

  return (
    <Dialog
      open={open}
      title={
        <span className="flex items-center gap-2">
          <Hand size={20} strokeWidth={1.75} aria-hidden="true" className="text-accent" />
          SecuLayer paused an action
        </span>
      }
      description="The assistant wants to send this email."
      initialFocus={cancelRef}
      onDismiss={() => decide(false)}
    >
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-3 text-small">
        <dt className="text-ink-3">To</dt>
        <dd>
          <ul className="space-y-1">
            {dialog.to.map((address) => (
              <li key={address} className="font-mono text-mono break-all text-ink">
                {address}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-ink-2">{dialog.reason}</p>
        </dd>
        <dt className="text-ink-3">Subject</dt>
        <dd className="break-words text-ink">{dialog.subject || "(no subject)"}</dd>
        <dt className="text-ink-3">Body</dt>
        <dd className="max-h-48 overflow-y-auto rounded-chip bg-surface-muted px-3 py-2 break-words whitespace-pre-wrap text-ink">
          {highlight(dialog.body, needles)}
        </dd>
      </dl>
      {dialog.highlights.length > 0 && (
        <p className="mt-3 text-small text-danger-ink">Private details are highlighted.</p>
      )}
      <p className="mt-5 text-body font-semibold text-ink">Would {userName} send this?</p>
      <div className="mt-4 flex items-center justify-between gap-3">
        <Button ref={cancelRef} variant="secondary" onClick={() => decide(false)}>
          Don't send
        </Button>
        <Button variant="secondary" onClick={() => decide(true)}>
          Send anyway
        </Button>
      </div>
    </Dialog>
  );
}
