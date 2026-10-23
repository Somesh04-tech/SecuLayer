import { clsx } from "clsx";
import { ChevronRight } from "lucide-react";
import { useId, useState } from "react";

import type { AnatomyMessage, AnatomyPart } from "../../../api/types";

const MESSAGE_STYLE: Record<AnatomyMessage["role"], string> = {
  developer: "border-l-dev-ink bg-dev-bg",
  user: "border-l-user-ink bg-user-bg",
  assistant: "border-l-border-strong bg-page",
  tool_call: "border-l-border-strong bg-page",
  tool_result: "border-l-outside-border bg-outside-bg",
};

const PART_STYLE: Record<AnatomyPart["source"], string> = {
  developer: "text-ink",
  user: "text-ink",
  external: "text-ink",
  model: "text-ink-2",
  injected: "rounded-chip bg-danger-bg text-danger-ink",
  seculayer: "rounded-chip bg-safe-bg text-safe-ink",
};

function hiddenLabel(part: AnatomyPart): string {
  if (part.hidden_kind === "tag_chars") {
    const decoded = [...part.text]
      .map((ch) => {
        const code = ch.codePointAt(0) ?? 0;
        return code >= 0xe0020 && code <= 0xe007e ? String.fromCharCode(code - 0xe0000) : "";
      })
      .join("");
    return `invisible tag characters: “${decoded}”`;
  }
  if (part.hidden_kind === "zero_width") return `${[...part.text].length} invisible characters`;
  return "";
}

function Part({ part }: { part: AnatomyPart }) {
  if (part.removed) {
    return (
      <span className="mx-0.5 inline-block rounded-chip border border-dashed border-safe-border px-1 font-ui text-caption text-safe-ink line-through">
        hidden text removed by SecuLayer
      </span>
    );
  }
  if (part.hidden_kind === "tag_chars" || part.hidden_kind === "zero_width") {
    return (
      <span className="mx-0.5 inline-block rounded-chip border border-danger-border px-1 font-ui text-caption text-danger-ink">
        {hiddenLabel(part)}
      </span>
    );
  }
  return (
    <span
      className={clsx(
        PART_STYLE[part.source],
        part.hidden && "underline decoration-danger-solid decoration-dotted underline-offset-4",
      )}
    >
      {part.text}
    </span>
  );
}

/**
 * A plain view of the last model request, colour-coded by source. Collapsed by default.
 * (The full prompt anatomy, with tabs, the share bar and the legend, is milestone M5.)
 */
export function AnatomyPreview({
  messages,
  callCount,
  sideLabel,
}: {
  messages: AnatomyMessage[] | null;
  callCount: number;
  sideLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  if (!messages) {
    return (
      <p className="flex items-center gap-2 border-t border-border pt-4 text-body text-ink-3">
        <ChevronRight size={16} strokeWidth={1.75} aria-hidden="true" />
        What the model received (run the attack first)
      </p>
    );
  }
  return (
    <section className="border-t border-border pt-4">
      <h2>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((o) => !o)}
          className="inline-flex items-center gap-2 text-body font-semibold text-ink hover:text-accent"
        >
          <ChevronRight
            size={16}
            strokeWidth={1.75}
            aria-hidden="true"
            className={clsx(
              "transition-transform duration-(--duration-expand) ease-standard",
              open && "rotate-90",
            )}
          />
          What the model received
        </button>
      </h2>
      {open && (
        <div id={id} className="mt-3">
          <p className="text-small text-ink-2">
            {sideLabel}: the last of {callCount} model {callCount === 1 ? "call" : "calls"}. Grey is
            the developer, plum is the user, amber is outside content and red is the attacker's
            text.
          </p>
          <ol className="mt-3 max-h-[36rem] space-y-2 overflow-y-auto">
            {messages.map((message, index) => (
              <li
                key={index}
                className={clsx("rounded-chip border-l-3 px-4 py-3", MESSAGE_STYLE[message.role])}
              >
                <p className="text-caption text-ink-2">{message.label}</p>
                {message.parts.length > 0 && (
                  <p className="mt-1 font-mono text-mono break-words whitespace-pre-wrap">
                    {message.parts.map((part, i) => (
                      <Part key={i} part={part} />
                    ))}
                  </p>
                )}
              </li>
            ))}
          </ol>
          <p className="mt-3 text-small text-ink-3">
            Why the model gets confused: these blocks reach the model as one sequence of text. Only
            the wording tells it which part came from a stranger.
          </p>
        </div>
      )}
    </section>
  );
}
