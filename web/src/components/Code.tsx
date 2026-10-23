import type { ReactNode } from "react";

/** Inline code: commands, file names, addresses. */
export function Code({ children }: { children: ReactNode }) {
  return <code className="rounded-chip bg-surface-muted px-1 font-mono">{children}</code>;
}
