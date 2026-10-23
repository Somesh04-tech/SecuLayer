import { ChevronRight } from "lucide-react";
import { useEffect } from "react";

import { ButtonLink } from "../components/Button";
import { Container } from "../components/Page";
import { Term } from "../components/Term";
import { PromptDiagram } from "../features/home/PromptDiagram";
import { ScenarioCards } from "../features/home/ScenarioCards";

export function HomePage() {
  useEffect(() => {
    document.title = "SecuLayer · Prompt injection, shown and stopped";
  }, []);

  return (
    <Container className="py-14">
      <section className="grid items-start gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,34rem)]">
        <div className="pt-2">
          <h1 className="max-w-[20ch] text-display text-ink">
            Watch an AI assistant get hijacked, then watch SecuLayer stop it.
          </h1>
          <p className="mt-6 max-w-prose text-lead text-ink-2">
            AI apps put their own instructions, your request and content from anywhere into one{" "}
            <Term id="prompt">prompt</Term>. If an attacker writes part of that content, they can
            give the AI orders.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-6">
            <ButtonLink to="/lab/inbox" variant="primary">
              Start with the inbox assistant
            </ButtonLink>
            <ButtonLink to="/how" variant="ghost" trailingIcon={ChevronRight}>
              How SecuLayer works
            </ButtonLink>
          </div>
        </div>
        <PromptDiagram />
      </section>

      <section className="mt-16" aria-labelledby="scenarios-heading">
        <h2 id="scenarios-heading" className="text-h2 text-ink">
          Choose a scenario
        </h2>
        <p className="mt-2 max-w-prose text-body text-ink-2">
          Four toy apps, each built the way many real apps are. The markers show which parts of the{" "}
          <Term id="lethalTrifecta">lethal trifecta</Term> each one has.
        </p>
        <div className="mt-6">
          <ScenarioCards />
        </div>
      </section>
    </Container>
  );
}
