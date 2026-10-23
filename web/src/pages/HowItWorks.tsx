import { Workflow } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { Page } from "../components/Page";

export function HowItWorksPage() {
  return (
    <Page
      title="How SecuLayer works"
      lead="SecuLayer sits between an AI app and the model. It checks what goes in and what comes out, in five layers."
    >
      <EmptyState
        icon={Workflow}
        title="The layer guide isn't written yet"
        help="This page will show SecuLayer's request flow and what each layer catches: the hidden-text cleaner, screening, prompt hardening, the tool guard and the output guard."
      />
    </Page>
  );
}
