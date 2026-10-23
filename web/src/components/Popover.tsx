import { clsx } from "clsx";
import { Popover as RadixPopover } from "radix-ui";
import type { ReactElement, ReactNode } from "react";

/** A Radix popover with the shared panel style: white, 10 px radius, popover shadow. */
export function Popover({
  trigger,
  label,
  children,
  className,
}: {
  trigger: ReactElement;
  /** Accessible name for the popover panel. */
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <RadixPopover.Root>
      <RadixPopover.Trigger asChild>{trigger}</RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content
          aria-label={label}
          align="end"
          sideOffset={8}
          collisionPadding={16}
          // Focus the panel, not its first focusable child: that is often a Term, and focusing it
          // would open a tooltip that swallows the first Escape.
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            (event.currentTarget as HTMLElement).focus();
          }}
          className={clsx(
            "z-40 w-popover max-w-[calc(100vw-2rem)] rounded-card border border-border bg-page p-5 text-small text-ink-2 shadow-popover",
            className,
          )}
        >
          {children}
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  );
}
