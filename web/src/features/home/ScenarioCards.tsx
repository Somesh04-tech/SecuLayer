import { RotateCw, TriangleAlert } from "lucide-react";
import { Link } from "react-router";

import { useApi } from "../../api/client";
import type { ScenarioSummary } from "../../api/types";
import { Button } from "../../components/Button";
import { ErrorState } from "../../components/EmptyState";
import { TrifectaMarkers } from "./Trifecta";

function isSummaryList(data: unknown): data is ScenarioSummary[] {
  return Array.isArray(data) && data.every((s) => typeof s === "object" && s && "id" in s);
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

function ScenarioCard({ scenario }: { scenario: ScenarioSummary }) {
  return (
    <li className="relative flex flex-col gap-3 rounded-card border border-border p-6 transition-colors duration-(--duration-hover) ease-standard hover:border-border-strong">
      <h3 className="text-h3 text-ink">
        <Link
          to={`/lab/${scenario.id}`}
          className="after:absolute after:inset-0 after:rounded-card hover:text-accent"
        >
          {scenario.title}
        </Link>
      </h3>
      <p className="max-w-prose text-body text-ink-2">{scenario.card_summary}</p>
      <p className="text-small text-ink-3">
        {scenario.injection} · {plural(scenario.attack_count, "attack", "attacks")} ·{" "}
        {scenario.normal_count} normal
      </p>
      <div className="mt-auto pt-1">
        <TrifectaMarkers trifecta={scenario.trifecta} compact />
      </div>
    </li>
  );
}

function SkeletonCards() {
  return (
    <ul aria-busy="true" aria-label="Loading scenarios" className="grid gap-6 md:grid-cols-2">
      {[0, 1, 2, 3].map((i) => (
        <li key={i} className="flex flex-col gap-3 rounded-card border border-border p-6">
          <span className="h-6 w-40 rounded-chip bg-surface-muted" />
          <span className="h-4 w-full rounded-chip bg-surface-muted" />
          <span className="h-4 w-3/4 rounded-chip bg-surface-muted" />
        </li>
      ))}
    </ul>
  );
}

/** The four scenario cards, from GET /api/scenarios. */
export function ScenarioCards() {
  const scenarios = useApi<ScenarioSummary[]>("/api/scenarios");

  if (scenarios.status === "loading") return <SkeletonCards />;
  if (scenarios.status === "error" || !isSummaryList(scenarios.data)) {
    return (
      <ErrorState
        icon={TriangleAlert}
        title="Couldn't load the scenarios."
        help="The server answered, but not with the scenario list."
        action={
          <Button variant="secondary" icon={RotateCw} onClick={scenarios.retry}>
            Try again
          </Button>
        }
      />
    );
  }
  return (
    <ul className="grid gap-6 md:grid-cols-2">
      {scenarios.data.map((scenario) => (
        <ScenarioCard key={scenario.id} scenario={scenario} />
      ))}
    </ul>
  );
}
