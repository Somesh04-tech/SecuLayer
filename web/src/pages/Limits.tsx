import { ChevronRight, RotateCw, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import type { EvalSummary } from "../api/eval";
import { Button, ButtonLink } from "../components/Button";
import { ErrorState } from "../components/EmptyState";
import { Page } from "../components/Page";
import { Term } from "../components/Term";
import { sourceById } from "../content/sources";
import { HardCase } from "../features/limits/HardCase";
import { Quotes } from "../features/limits/Quotes";
import { useEvalSummary } from "../features/results/useEvalSummary";
import { ExternalLink } from "../features/sources/ExternalLink";

function classifierLine(summary: EvalSummary | null): string {
  const layer = summary?.layers.find((l) => l.id === "classifier");
  const caught = layer?.caught;
  if (!caught) return "";
  return ` In the evaluation it would have intervened in ${caught.count} of ${caught.total} attack runs.`;
}

function SmallLimits({ summary }: { summary: EvalSummary | null }) {
  const forcedleak = sourceById("forcedleak");
  const echoleak = sourceById("echoleak");
  const owaspAgentic = sourceById("owasp-agentic-2026");
  const items: { title: string; body: ReactNode }[] = [
    {
      title: "Encodings we don't decode",
      body: "The output guard reads Base64, hex, reversed text and separators. A secret spelled as an acrostic, translated, or turned into a riddle slips through, and the model can produce all of those.",
    },
    {
      title: "Confirmation fatigue",
      body: (
        <>
          Asking Dana is only as good as Dana's attention. People approve convincing requests,
          especially after many harmless ones: the{" "}
          <ExternalLink href={owaspAgentic.links[0]?.url ?? ""}>OWASP Agentic Top 10</ExternalLink>{" "}
          lists this as ASI09, human-agent trust exploitation.
        </>
      ),
    },
    {
      title: "Allowlisted sites that host attacker content",
      body: (
        <>
          The output guard trusts allowlisted domains. ForcedLeak reused an expired allowlisted
          domain (<ExternalLink href={forcedleak.links[0]?.url ?? ""}>Noma Security</ExternalLink>
          ), and EchoLeak went out through an allowed Microsoft Teams address (
          <ExternalLink href={echoleak.links[0]?.url ?? ""}>Aim Security</ExternalLink>).
        </>
      ),
    },
    {
      title: "Rules fit the attacks they were written against",
      body: "The screening rules were written knowing this demo's attacks. Paraphrases, typos and other languages slip past them, and normal text can trip them; the variants and the normal-use bait measure both.",
    },
    {
      title: "The classifier misses context-dependent injections",
      body: (
        <>
          The <Term id="classifier">classifier</Term> catches explicit attack phrasing, like “ignore
          all previous instructions”, but not polite requests or text addressed to an assistant in
          ordinary words.{classifierLine(summary)}
        </>
      ),
    },
  ];
  return (
    <section aria-labelledby="limits-more" className="mt-14">
      <h2 id="limits-more" className="text-h2 text-ink">
        Smaller gaps
      </h2>
      <dl className="mt-4 max-w-prose divide-y divide-border border-y border-border">
        {items.map((item) => (
          <div key={item.title} className="py-4">
            <dt className="text-body font-semibold text-ink">{item.title}</dt>
            <dd className="mt-1 text-body text-ink-2">{item.body}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function LimitsPage() {
  const state = useEvalSummary();
  const summary = state.status === "ok" ? state.data : null;
  const nasr = sourceById("nasr-2025");

  return (
    <Page
      title="What SecuLayer can't stop"
      lead="Prompt injection isn't solved. Here is where this demo's defenses fall short, and why."
    >
      <p className="max-w-prose text-body text-ink-2">
        SecuLayer lowers the <Term id="attackSuccessRate">attack success rate</Term> a lot, but{" "}
        <Term id="promptInjection">prompt injection</Term> exploits the fact that the model reads
        instructions and data as one text. Two attacks in this demo show where filtering can't help.
      </p>
      {state.status === "missing" && (
        <p className="mt-3 text-small text-ink-3">
          The evaluation hasn't run, so the numbers are missing. Run{" "}
          <code className="font-mono text-mono">make eval</code> to measure them.
        </p>
      )}
      {state.status === "error" && (
        <div className="mt-6">
          <ErrorState
            icon={TriangleAlert}
            title="The measured numbers didn't load."
            help={state.error.message}
            action={
              <Button variant="secondary" icon={RotateCw} onClick={state.retry}>
                Try again
              </Button>
            }
          />
        </div>
      )}

      <section aria-labelledby="limits-hard" className="mt-10">
        <h2 id="limits-hard" className="text-h2 text-ink">
          The two hard cases
        </h2>
        <div className="mt-6 grid gap-6 xl:grid-cols-2">
          <HardCase
            id="inbox.polite_invoice"
            title="The polite invoice"
            labLink="/lab/inbox?case=inbox.polite_invoice"
            summary={summary}
          >
            <p>
              Nothing is hidden and nothing is addressed to an AI. The email reads like real
              business, and Dana did ask the assistant to handle urgent email.
            </p>
            <p>
              Telling it apart from a real vendor takes knowledge the software doesn't have. The
              tool guard can only turn the send into a question for Dana: if she approves, the
              attack succeeds.
            </p>
          </HardCase>
          <HardCase
            id="helpdesk.misinformation"
            title="The fake policy"
            labLink="/lab/helpdesk?case=helpdesk.misinformation"
            summary={summary}
          >
            <p>
              A false fact is not an instruction, so no filter can flag it. An edited wiki page says
              employees may expense $5,000 without approval, and the assistant does its job: it
              answers from the best-matching page.
            </p>
            <p>
              The output checks can't know a number is wrong. The real fix is controlling who can
              edit the knowledge base, not filtering what the model reads.
            </p>
          </HardCase>
        </div>
      </section>

      <section aria-labelledby="limits-adapt" className="mt-14">
        <h2 id="limits-adapt" className="text-h2 text-ink">
          Attackers adapt
        </h2>
        <p className="mt-3 max-w-prose text-body text-ink-2">
          Our attacks were written against the unprotected app. An attacker who studies SecuLayer
          does better: researchers broke 12 published defenses by adapting their attacks to each one
          (<ExternalLink href={nasr.links[0]?.url ?? ""}>Nasr et al., 2025</ExternalLink>
          ). The rates on the Results page are an upper bound on how well SecuLayer would do against
          someone who knows it.
        </p>
      </section>

      <SmallLimits summary={summary} />

      <section aria-labelledby="limits-help" className="mt-14">
        <h2 id="limits-help" className="text-h2 text-ink">
          What would help more
        </h2>
        <p className="mt-3 max-w-prose text-body text-ink-2">
          Designs that keep untrusted text away from decisions: a model that can use tools never
          reads the email, or the plan is fixed before any outside content arrives. They cost
          flexibility, but they don't depend on spotting the attack.
        </p>
        <div className="mt-3">
          <ButtonLink to="/how#patterns" variant="ghost" trailingIcon={ChevronRight}>
            Patterns this demo explains but doesn't build
          </ButtonLink>
        </div>
      </section>

      <Quotes />
    </Page>
  );
}
