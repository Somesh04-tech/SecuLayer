import { clsx } from "clsx";
import {
  CircleAlert,
  CircleCheck,
  CircleX,
  Hand,
  Info,
  OctagonX,
  type LucideIcon,
} from "lucide-react";

import type { Outcome, RunFinished } from "../../../api/types";

interface BannerStyle {
  icon: LucideIcon;
  box: string;
  icon_: string;
  title: string;
}

const STYLES: Record<Outcome, BannerStyle> = {
  hijacked: {
    icon: OctagonX,
    box: "border-danger-border bg-danger-bg",
    icon_: "text-danger-solid",
    title: "text-danger-ink",
  },
  stopped: {
    icon: CircleCheck,
    box: "border-safe-border bg-safe-bg",
    icon_: "text-safe-solid",
    title: "text-safe-ink",
  },
  resisted: {
    icon: CircleCheck,
    box: "border-safe-border bg-safe-bg",
    icon_: "text-safe-solid",
    title: "text-safe-ink",
  },
  paused: {
    icon: Hand,
    box: "border-accent-subtle bg-accent-subtle",
    icon_: "text-accent",
    title: "text-accent",
  },
  completed: {
    icon: CircleCheck,
    box: "border-border-strong bg-page",
    icon_: "text-ink-2",
    title: "text-ink",
  },
  false_alarm: {
    icon: Info,
    box: "border-border-strong bg-surface-muted",
    icon_: "text-ink-2",
    title: "text-ink",
  },
  failed: {
    icon: CircleX,
    box: "border-border-strong bg-page",
    icon_: "text-ink-2",
    title: "text-ink",
  },
  error: {
    icon: CircleAlert,
    box: "border-border-strong bg-page",
    icon_: "text-ink-2",
    title: "text-ink",
  },
};

/** The outcome, in the fixed banner shape: bold outcome word, colon, one sentence (§3.5). */
export function OutcomeBanner({
  outcome,
  banner,
}: {
  outcome: Outcome;
  banner: RunFinished["banner"];
}) {
  const style = STYLES[outcome];
  const Icon = style.icon;
  return (
    <div
      data-testid="outcome-banner"
      data-outcome={outcome}
      className={clsx("flex items-start gap-3 rounded-card border px-4 py-3", style.box)}
    >
      <Icon
        size={20}
        strokeWidth={1.75}
        aria-hidden="true"
        className={clsx("mt-0.5 shrink-0", style.icon_)}
      />
      <p className="text-body text-ink">
        <strong className={clsx("font-bold", style.title)}>{banner.title}</strong>
        {banner.sentence ? `: ${banner.sentence}` : ""}
      </p>
    </div>
  );
}
