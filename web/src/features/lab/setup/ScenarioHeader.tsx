import { ChevronRight } from "lucide-react";
import { Link } from "react-router";

import type { ScenarioDetail } from "../../../api/types";
import { Disclosure } from "../../../components/Disclosure";
import { Term } from "../../../components/Term";
import { TrifectaMarkers } from "../../home/Trifecta";

/** The scenario's title, summary, trifecta and "How this app is built". */
export function ScenarioHeader({ scenario }: { scenario: ScenarioDetail }) {
  const direct = scenario.injection.toLowerCase().startsWith("direct");
  return (
    <header className="space-y-4">
      <nav aria-label="Breadcrumb">
        <ol className="flex items-center gap-1.5 text-small">
          <li>
            <Link
              to="/lab"
              className="font-semibold text-accent underline-offset-4 hover:text-accent-hover hover:underline"
            >
              All scenarios
            </Link>
          </li>
          <li aria-hidden="true" className="text-ink-3">
            <ChevronRight size={14} strokeWidth={1.75} />
          </li>
          <li aria-current="page" className="text-ink-2">
            {scenario.title}
          </li>
        </ol>
      </nav>
      <div>
        <h1 className="text-h1 text-ink">{scenario.title}</h1>
        <p className="mt-2 max-w-prose text-lead text-ink-2">{scenario.summary}</p>
        <p className="mt-2 text-small text-ink-3">
          {direct ? (
            <Term id="directInjection">Direct injection</Term>
          ) : (
            <Term id="indirectInjection">Indirect injection</Term>
          )}{" "}
          · the <Term id="lethalTrifecta">lethal trifecta</Term> in this app:
        </p>
        <div className="mt-2">
          <TrifectaMarkers trifecta={scenario.trifecta} />
        </div>
      </div>
      <Disclosure title="How this app is built">
        <div className="max-w-prose space-y-4">
          <ul className="list-disc space-y-1 pl-5 text-body text-ink-2">
            {scenario.how_built.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <div>
            <p className="text-small font-semibold text-dev-ink">
              <Term id="developerInstructions">Developer instructions (the system prompt)</Term>
            </p>
            <pre className="mt-2 rounded-control border-l-3 border-dev-ink bg-dev-bg p-4 font-mono text-mono break-words whitespace-pre-wrap text-ink">
              {scenario.developer_instructions}
            </pre>
          </div>
        </div>
      </Disclosure>
    </header>
  );
}
