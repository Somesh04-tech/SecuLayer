import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface StateProps {
  icon: LucideIcon;
  title: ReactNode;
  help?: ReactNode;
  action?: ReactNode;
}

function StatePanel({ icon: Icon, title, help, action, role }: StateProps & { role?: "alert" }) {
  return (
    <div
      role={role}
      className="flex flex-col items-start gap-2 rounded-card border border-border px-6 py-8"
    >
      <Icon size={24} strokeWidth={1.75} className="text-ink-3" aria-hidden="true" />
      <p className="mt-1 text-body font-semibold text-ink">{title}</p>
      {help && <p className="max-w-prose text-small text-ink-2">{help}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

/** Nothing to show yet: an icon, a one-line title, one line of help and an optional action. */
export function EmptyState(props: StateProps) {
  return <StatePanel {...props} />;
}

/** Something went wrong. Announced to screen readers. */
export function ErrorState(props: StateProps) {
  return <StatePanel {...props} role="alert" />;
}
