import { Tooltip as RadixTooltip } from "radix-ui";
import type { ReactElement, ReactNode } from "react";

export const TooltipProvider = RadixTooltip.Provider;

/** A small white tooltip, at most 320 px wide. The trigger must be focusable. */
export function Tooltip({ content, children }: { content: ReactNode; children: ReactElement }) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          sideOffset={6}
          collisionPadding={16}
          className="z-50 max-w-tooltip rounded-control border border-border bg-page px-3 py-2 text-small text-ink-2 shadow-popover"
        >
          {content}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
