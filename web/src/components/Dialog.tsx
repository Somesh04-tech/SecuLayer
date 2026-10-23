import { Dialog as RadixDialog } from "radix-ui";
import type { ReactNode, RefObject } from "react";

/**
 * A modal dialog, 560 px wide (§4.5). Closing it any way other than an explicit button
 * (Escape, the overlay) calls `onDismiss`.
 */
export function Dialog({
  open,
  title,
  description,
  initialFocus,
  onDismiss,
  children,
}: {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  /** The element focused when the dialog opens. */
  initialFocus?: RefObject<HTMLElement | null>;
  onDismiss: () => void;
  children: ReactNode;
}) {
  return (
    <RadixDialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!next) onDismiss();
      }}
    >
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-overlay" />
        <RadixDialog.Content
          onOpenAutoFocus={(event) => {
            if (initialFocus?.current) {
              event.preventDefault();
              initialFocus.current.focus();
            }
          }}
          className="fixed top-1/2 left-1/2 z-50 max-h-[calc(100vh-4rem)] w-[35rem] max-w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-card border border-border bg-page p-6 shadow-popover"
        >
          <RadixDialog.Title className="text-h3 text-ink">{title}</RadixDialog.Title>
          {description ? (
            <RadixDialog.Description className="mt-1 text-body text-ink-2">
              {description}
            </RadixDialog.Description>
          ) : (
            <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
          )}
          <div className="mt-5">{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
