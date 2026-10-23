import { clsx } from "clsx";
import { Fingerprint, Globe, Minus, Send, type LucideIcon } from "lucide-react";

import { Tooltip } from "../../components/Tooltip";

type Ingredient = "private_data" | "outside_content" | "way_out";

const INGREDIENTS: { key: Ingredient; label: string; icon: LucideIcon }[] = [
  { key: "private_data", label: "Private data", icon: Fingerprint },
  { key: "outside_content", label: "Outside content", icon: Globe },
  { key: "way_out", label: "Way out", icon: Send },
];

/** An ingredient is absent when the scenario describes it as "none: …" (the support chat). */
function absent(text: string | undefined): boolean {
  return !text || /^none\b/i.test(text);
}

function absentNote(text: string | undefined): string {
  if (!text) return "Not part of this app.";
  return text.includes("types the instructions directly")
    ? "Here the attacker types the instructions directly."
    : text.replace(/^none:\s*/i, "");
}

/**
 * The three "lethal trifecta" markers. `compact` (scenario cards) shows labels with tooltips;
 * the full form (Lab header) spells each ingredient out.
 */
export function TrifectaMarkers({
  trifecta,
  compact = false,
}: {
  trifecta: Record<string, string>;
  compact?: boolean;
}) {
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-2" aria-label="Lethal trifecta">
      {INGREDIENTS.map(({ key, label, icon: Icon }) => {
        const text = trifecta[key];
        const missing = absent(text);
        const MarkerIcon = missing ? Minus : Icon;
        const marker = (
          <span
            className={clsx(
              "inline-flex items-center gap-1.5 text-small",
              missing ? "text-ink-3" : "text-ink-2",
            )}
          >
            <MarkerIcon
              size={16}
              strokeWidth={1.75}
              aria-hidden="true"
              className={missing ? "text-ink-3" : "text-ink"}
            />
            <span className={clsx(!missing && "font-semibold text-ink")}>{label}</span>
            {!compact && (
              <span>{missing ? `: ${absentNote(text).toLowerCase()}` : `: ${text}`}</span>
            )}
            {missing && <span className="sr-only">(not present)</span>}
          </span>
        );
        return (
          <li key={key} className="relative z-10">
            {compact ? (
              <Tooltip content={missing ? absentNote(text) : `${label}: ${text}`}>
                <button
                  type="button"
                  className="cursor-help rounded-chip underline decoration-ink-3 decoration-dotted decoration-1 underline-offset-3"
                >
                  {marker}
                </button>
              </Tooltip>
            ) : (
              marker
            )}
          </li>
        );
      })}
    </ul>
  );
}
