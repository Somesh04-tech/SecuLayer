import type { ReactNode } from "react";

import { glossary, type GlossaryId } from "../content/glossary";
import { Tooltip } from "./Tooltip";

/** A glossary term: dotted underline, definition on hover or keyboard focus (§3.5). */
export function Term({ id, children }: { id: GlossaryId; children?: ReactNode }) {
  const entry = glossary[id];
  return (
    <Tooltip
      content={
        <>
          <span className="block font-semibold text-ink">{entry.term}</span>
          {entry.definition}
        </>
      }
    >
      <button
        type="button"
        className="cursor-help underline decoration-ink-3 decoration-dotted decoration-1 underline-offset-3"
      >
        {children ?? entry.term}
      </button>
    </Tooltip>
  );
}
