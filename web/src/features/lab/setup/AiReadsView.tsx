import { clsx } from "clsx";
import { EyeOff, Globe, TriangleAlert, UserRound } from "lucide-react";

import type { ReadPart } from "../../../api/types";
import { Chip } from "../../../components/Chip";

const ZERO_WIDTH: Record<number, string> = {
  0x200b: "ZWSP",
  0x200c: "ZWNJ",
  0x200d: "ZWJ",
  0x2060: "WJ",
  0xfeff: "BOM",
};

const HIDDEN_LABEL: Record<NonNullable<ReadPart["hidden_kind"]>, string> = {
  css: "Hidden: CSS",
  comment: "HTML comment",
  tag_chars: "Invisible characters",
  zero_width: "Invisible characters",
};

/** Unicode tag characters (U+E0020–U+E007E) map one-to-one onto ASCII. */
export function decodeTags(text: string): string {
  return [...text]
    .map((ch) => ch.codePointAt(0) ?? 0)
    .filter((code) => code >= 0xe0020 && code <= 0xe007e)
    .map((code) => String.fromCodePoint(code - 0xe0000))
    .join("");
}

function invisibleChips(text: string) {
  return [...text].map((ch, i) => {
    const code = ch.codePointAt(0) ?? 0;
    const label = ZERO_WIDTH[code] ?? `U+${code.toString(16).toUpperCase().padStart(4, "0")}`;
    return (
      <Chip key={i} tone="danger" className="mx-0.5 align-baseline font-ui">
        {label}
      </Chip>
    );
  });
}

function Part({ part }: { part: ReadPart }) {
  const injected = part.source === "injected";
  if (part.hidden_kind === "tag_chars") {
    return (
      <span className="rounded-chip border border-danger-border bg-danger-bg px-1 text-danger-ink">
        <Chip tone="danger" icon={EyeOff} className="mr-1 align-baseline font-ui">
          Invisible
        </Chip>
        {decodeTags(part.text)}
      </span>
    );
  }
  if (part.hidden_kind === "zero_width") return <>{invisibleChips(part.text)}</>;
  return (
    <span
      className={clsx(
        injected && "rounded-chip bg-danger-bg text-danger-ink",
        part.hidden && "underline decoration-danger-solid decoration-2 underline-offset-3",
        part.source === "user" && "text-user-ink",
      )}
    >
      {part.text}
      {part.hidden && part.hidden_kind && (
        <Chip tone="danger" icon={EyeOff} className="ml-1 align-baseline font-ui">
          {HIDDEN_LABEL[part.hidden_kind]}
        </Chip>
      )}
    </span>
  );
}

/**
 * "Show what the AI reads": the raw text the app passes to the model, with the attacker's
 * injected text in red and anything a person wouldn't see marked as hidden.
 */
export function AiReadsView({
  parts,
  label,
  note,
}: {
  parts: ReadPart[];
  label: string;
  note?: string;
}) {
  const userText = parts.some((p) => p.source === "user");
  const hasInjected = parts.some((p) => p.source === "injected");
  const hasHidden = parts.some((p) => p.hidden);
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2" aria-label="Legend">
        {userText ? (
          <Chip tone="user" icon={UserRound}>
            User
          </Chip>
        ) : (
          <Chip tone="outside" icon={Globe}>
            Outside content
          </Chip>
        )}
        {hasInjected && (
          <Chip tone="danger" icon={TriangleAlert}>
            Injected by the attacker
          </Chip>
        )}
        {hasHidden && (
          <Chip tone="danger" icon={EyeOff}>
            Hidden from Dana
          </Chip>
        )}
      </div>
      {note && <p className="text-small text-ink-3">{note}</p>}
      <div
        role="region"
        aria-label={label}
        // A focusable scroll region, so keyboard users can scroll long sources.
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
        tabIndex={0}
        className={clsx(
          "max-h-[28rem] overflow-auto rounded-control border-l-3 p-4 font-mono text-mono break-words whitespace-pre-wrap text-ink",
          userText ? "border-user-ink bg-user-bg" : "border-outside-border bg-outside-bg",
        )}
      >
        {parts.map((part, i) => (
          <Part key={i} part={part} />
        ))}
      </div>
    </div>
  );
}
