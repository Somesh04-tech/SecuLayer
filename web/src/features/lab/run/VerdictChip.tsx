import { clsx } from "clsx";
import { Check, CircleSlash, Hand, Layers, Minus, type LucideIcon } from "lucide-react";

import type { VerdictAction } from "../../../api/types";
import { capitalise } from "./labels";

interface ChipStyle {
  label: string;
  icon: LucideIcon;
  className: string;
}

/** The §4.2 verdict styles. Chips stay neutral: the outcome banner carries the meaning. */
export function verdictStyle(action: VerdictAction, userName: string): ChipStyle {
  switch (action) {
    case "blocked":
    case "withheld":
    case "removed":
      return {
        label: capitalise(action),
        icon: CircleSlash,
        className: "border border-ink bg-ink text-page",
      };
    case "confirm":
      return {
        label: `Asked ${userName}`,
        icon: Hand,
        className: "border border-accent-subtle bg-accent-subtle text-accent",
      };
    case "applied":
      return {
        label: "Applied",
        icon: Layers,
        className: "border border-border-strong bg-page text-ink-2",
      };
    case "passed":
    case "flagged":
      return {
        label: action === "passed" ? "Passed" : "Flagged",
        icon: Check,
        className: "border border-border bg-page text-ink-3",
      };
    case "off":
    case "not_reached":
    case "unavailable":
      return {
        label: action === "off" ? "Off" : action === "not_reached" ? "Not reached" : "Unavailable",
        icon: Minus,
        className: "border border-dashed border-border bg-page text-ink-3",
      };
  }
}

export function VerdictChip({ action, userName }: { action: VerdictAction; userName: string }) {
  const style = verdictStyle(action, userName);
  const Icon = style.icon;
  return (
    <span
      className={clsx(
        "inline-flex h-6 w-32 shrink-0 items-center gap-1.5 rounded-chip px-2 text-caption whitespace-nowrap",
        style.className,
      )}
    >
      <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
      {style.label}
    </span>
  );
}
