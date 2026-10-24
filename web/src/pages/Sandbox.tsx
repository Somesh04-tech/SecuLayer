import { clsx } from "clsx";
import { useId } from "react";
import { useSearchParams } from "react-router";

import { Page } from "../components/Page";
import { Term } from "../components/Term";
import { SandboxWorkbench } from "../features/sandbox/SandboxWorkbench";
import { SANDBOX_SCENARIOS, sandboxScenario } from "../features/sandbox/sandboxScenarios";

export function SandboxPage() {
  const [params, setParams] = useSearchParams();
  const selected = sandboxScenario(params.get("app") ?? "inbox");
  const legendId = useId();

  return (
    <Page
      title="Try your own"
      lead={
        <>
          Write the attacker's text yourself and see what SecuLayer makes of it. You control the{" "}
          <Term id="outsideContent">outside content</Term> (or, in the support chat, the customer's
          message) of a real <Term id="promptInjection">prompt injection</Term> case.
        </>
      }
    >
      <div className="space-y-10">
        <fieldset aria-labelledby={legendId}>
          <legend id={legendId} className="text-small font-semibold text-ink">
            Toy app
          </legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {SANDBOX_SCENARIOS.map((scenario) => {
              const checked = scenario.id === selected.id;
              return (
                <label
                  key={scenario.id}
                  className={clsx(
                    "inline-flex h-10 cursor-pointer items-center gap-2 rounded-control border px-4 text-small font-semibold",
                    "transition-colors duration-(--duration-hover) ease-standard",
                    "has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent",
                    checked
                      ? "border-accent bg-accent-subtle text-accent"
                      : "border-border-control bg-page text-ink hover:border-ink-2",
                  )}
                >
                  <input
                    type="radio"
                    name="sandbox-app"
                    value={scenario.id}
                    checked={checked}
                    onChange={() => setParams({ app: scenario.id }, { replace: true })}
                    className="sr-only"
                  />
                  {scenario.label}
                </label>
              );
            })}
          </div>
        </fieldset>
        <SandboxWorkbench key={selected.id} scenarioId={selected.id} />
      </div>
    </Page>
  );
}
