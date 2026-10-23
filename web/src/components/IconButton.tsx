import { clsx } from "clsx";
import type { ComponentPropsWithRef } from "react";
import type { LucideIcon } from "lucide-react";

import { Tooltip } from "./Tooltip";

export type IconButtonProps = {
  /** Accessible name, also shown as the tooltip unless `tooltip` is given. */
  label: string;
  tooltip?: string;
  icon: LucideIcon;
} & Omit<ComponentPropsWithRef<"button">, "children" | "aria-label">;

/** A 36 px square button with an aria-label and a tooltip. */
export function IconButton({ label, tooltip, icon: Icon, className, ...props }: IconButtonProps) {
  return (
    <Tooltip content={tooltip ?? label}>
      <button
        type="button"
        aria-label={label}
        className={clsx(
          "inline-flex size-9 shrink-0 items-center justify-center rounded-control border border-border-control bg-page text-ink",
          "transition-colors duration-(--duration-hover) ease-standard hover:border-ink-2",
          "aria-pressed:border-accent aria-pressed:bg-accent-subtle aria-pressed:text-accent",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      >
        <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
      </button>
    </Tooltip>
  );
}
