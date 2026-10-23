import { clsx } from "clsx";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export type ChipTone = "neutral" | "strong" | "outside" | "user" | "danger" | "safe" | "dev";

const TONES: Record<ChipTone, string> = {
  neutral: "border-border-strong bg-page text-ink-2",
  strong: "border-ink bg-page text-ink",
  outside: "border-outside-border bg-outside-bg text-outside-ink",
  user: "border-user-border bg-user-bg text-user-ink",
  danger: "border-danger-border bg-danger-bg text-danger-ink",
  safe: "border-safe-border bg-safe-bg text-safe-ink",
  dev: "border-dev-border bg-dev-bg text-dev-ink",
};

/**
 * A 24 px tag (§4.5): technique tags (neutral outline), source labels (tinted), the
 * "Hard case" tag (strong ink outline).
 */
export function Chip({
  tone = "neutral",
  icon: Icon,
  children,
  className,
}: {
  tone?: ChipTone;
  icon?: LucideIcon | undefined;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex h-6 shrink-0 items-center gap-1 rounded-chip border px-2 text-caption whitespace-nowrap",
        TONES[tone],
        className,
      )}
    >
      {Icon && <Icon size={14} strokeWidth={1.75} aria-hidden="true" />}
      {children}
    </span>
  );
}
