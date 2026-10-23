import { useEffect, useState } from "react";

import { Button } from "../../components/Button";
import { Dialog } from "../../components/Dialog";

export const SHORTCUTS: { keys: string; does: string }[] = [
  { keys: "[", does: "Previous case" },
  { keys: "]", does: "Next case" },
  { keys: "u", does: "Run without SecuLayer" },
  { keys: "s", does: "Run with SecuLayer" },
  { keys: "p", does: "Jump to what the model received" },
  { keys: "?", does: "Show these shortcuts" },
];

/** True when a key press belongs to a text field or another control, not to the page. */
export function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

export interface ShortcutActions {
  previous: () => void;
  next: () => void;
  run: (side: "without" | "with") => void;
  prompt: () => void;
}

/**
 * Presenter shortcuts for the Attack Lab (§9 M5). They're ignored while typing in a field,
 * with a modifier key held, or while a dialog is open.
 */
export function usePresenterShortcuts(actions: ShortcutActions) {
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
      if (isTyping(event.target)) return;
      if (document.querySelector("[role=dialog], [role=alertdialog]")) return;
      const handlers: Record<string, () => void> = {
        "[": actions.previous,
        "]": actions.next,
        u: () => actions.run("without"),
        s: () => actions.run("with"),
        p: actions.prompt,
        "?": () => setHelpOpen(true),
      };
      const handler = handlers[event.key];
      if (!handler) return;
      event.preventDefault();
      handler();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [actions]);

  return { helpOpen, closeHelp: () => setHelpOpen(false) };
}

export function ShortcutHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog
      open={open}
      title="Presenter shortcuts"
      description="They work anywhere in the Attack Lab, except while typing in a field."
      onDismiss={onClose}
    >
      <dl className="grid grid-cols-[3rem_minmax(0,1fr)] gap-x-4 gap-y-2 text-body">
        {SHORTCUTS.map((s) => (
          <div key={s.keys} className="contents">
            <dt>
              <kbd className="inline-flex min-w-7 justify-center rounded-chip border border-border-strong px-1.5 font-mono text-mono text-ink">
                {s.keys}
              </kbd>
            </dt>
            <dd className="text-ink-2">{s.does}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-6 flex justify-end">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>
    </Dialog>
  );
}
