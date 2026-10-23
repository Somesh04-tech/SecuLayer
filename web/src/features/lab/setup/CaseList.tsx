import { clsx } from "clsx";
import { useRef, type KeyboardEvent } from "react";

import type { CaseDetail } from "../../../api/types";
import { Chip } from "../../../components/Chip";

/** The cases the Lab lists: primary attacks (variants are for the evaluation) and normal use. */
export function listedCases(cases: CaseDetail[]): { attacks: CaseDetail[]; normal: CaseDetail[] } {
  return {
    attacks: cases.filter((c) => c.kind === "attack" && c.variant_of === null),
    normal: cases.filter((c) => c.kind === "normal"),
  };
}

function CaseOption({
  item,
  selected,
  onSelect,
  onKeyDown,
  index,
}: {
  item: CaseDetail;
  selected: boolean;
  onSelect: (id: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLDivElement>) => void;
  index: number;
}) {
  const tags = item.tags.filter((t) => t !== "Hard case");
  return (
    <div
      role="option"
      id={`case-${item.id}`}
      aria-selected={selected}
      tabIndex={selected ? 0 : -1}
      data-index={index}
      onClick={() => onSelect(item.id)}
      onKeyDown={onKeyDown}
      className={clsx(
        "cursor-pointer border-l-3 px-4 py-3 transition-colors duration-(--duration-hover) ease-standard",
        selected ? "border-accent bg-accent-subtle" : "border-transparent hover:bg-surface-muted",
      )}
    >
      <span
        className={clsx("block text-small font-semibold", selected ? "text-accent" : "text-ink")}
      >
        {item.title}
      </span>
      {(tags.length > 0 || item.hard_case) && (
        <span className="mt-1.5 flex flex-wrap gap-1.5">
          {item.hard_case && <Chip tone="strong">Hard case</Chip>}
          {tags.map((tag) => (
            <Chip key={tag}>{tag}</Chip>
          ))}
        </span>
      )}
    </div>
  );
}

/**
 * The Lab's left column (§4.5): "Attacks" and "Normal use". Up and down arrows (and Home,
 * End) move between items; Enter or Space selects.
 */
export function CaseList({
  cases,
  selectedId,
  onSelect,
}: {
  cases: CaseDetail[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const list = useRef<HTMLDivElement>(null);
  const { attacks, normal } = listedCases(cases);
  const ordered = [...attacks, ...normal];

  function focusAt(index: number) {
    const options = list.current?.querySelectorAll<HTMLElement>('[role="option"]');
    if (!options || options.length === 0) return;
    const clamped = Math.max(0, Math.min(options.length - 1, index));
    options.forEach((option, i) => (option.tabIndex = i === clamped ? 0 : -1));
    options[clamped]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    const index = Number(target.dataset.index ?? -1);
    if (index < 0) return;
    const moves: Record<string, number> = {
      ArrowDown: index + 1,
      ArrowUp: index - 1,
      Home: 0,
      End: ordered.length - 1,
    };
    if (event.key in moves) {
      event.preventDefault();
      focusAt(moves[event.key] ?? index);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      const item = ordered[index];
      if (item) onSelect(item.id);
    }
  }

  const group = (title: string, items: CaseDetail[], offset: number) => (
    <div
      role="group"
      aria-labelledby={`cases-${title.replace(/\s+/g, "-")}`}
      className="mt-6 first:mt-0"
    >
      <span
        id={`cases-${title.replace(/\s+/g, "-")}`}
        className="block px-4 text-small font-semibold text-ink-3"
      >
        {title}
      </span>
      <div className="mt-2">
        {items.map((item, i) => (
          <CaseOption
            key={item.id}
            item={item}
            index={offset + i}
            selected={item.id === selectedId}
            onSelect={onSelect}
            onKeyDown={onKeyDown}
          />
        ))}
      </div>
    </div>
  );

  return (
    // Focus sits on the options (roving tabindex), so the listbox itself isn't a tab stop.
    <div ref={list} role="listbox" aria-label="Cases" tabIndex={-1}>
      {group("Attacks", attacks, 0)}
      {normal.length > 0 && group("Normal use", normal, attacks.length)}
    </div>
  );
}
