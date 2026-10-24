import { Page } from "../components/Page";
import { Term } from "../components/Term";
import { FlowDiagram } from "../features/how/FlowDiagram";
import { LayerCards } from "../features/how/LayerCards";
import { Patterns } from "../features/how/Patterns";

export function HowItWorksPage() {
  return (
    <Page
      title="How SecuLayer works"
      lead="SecuLayer sits between an AI app and the model. It checks what goes in and what comes out, in five layers."
    >
      <section aria-labelledby="flow-heading">
        <h2 id="flow-heading" className="text-h2 text-ink">
          The request flow
        </h2>
        <p className="mt-2 max-w-prose text-body text-ink-2">
          The app hands SecuLayer its <Term id="prompt">prompt</Term> as labelled parts:{" "}
          <Term id="developerInstructions">developer instructions (the system prompt)</Term>, the
          user's request and <Term id="outsideContent">outside content</Term>. SecuLayer never edits
          the app's instructions or code. Each layer can be switched off, and each reports a verdict
          with a one-line reason.
        </p>
        <div className="mt-6">
          <FlowDiagram />
        </div>
      </section>

      <section aria-labelledby="layers-heading" className="mt-16">
        <h2 id="layers-heading" className="text-h2 text-ink">
          The five layers
        </h2>
        <p className="mt-2 max-w-prose text-body text-ink-2">
          Screening combines rules, a <Term id="classifier">classifier</Term> and an{" "}
          <Term id="llmJudge">LLM judge</Term>. Prompt hardening uses{" "}
          <Term id="spotlighting">spotlighting</Term>. The tool guard checks each{" "}
          <Term id="toolCall">tool call</Term>, and the output guard watches for{" "}
          <Term id="exfiltration">exfiltration</Term> and the{" "}
          <Term id="canaryToken">canary token</Term>. The measured numbers come from the recorded
          runs on the Results page.
        </p>
        <div className="mt-6">
          <LayerCards />
        </div>
      </section>

      <section aria-labelledby="patterns-heading" className="mt-16">
        <h2 id="patterns-heading" className="text-h2 text-ink">
          Patterns this demo explains but doesn't build
        </h2>
        <Patterns />
      </section>
    </Page>
  );
}
