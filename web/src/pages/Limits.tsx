import { BookOpen } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { Page } from "../components/Page";

export function LimitsPage() {
  return (
    <Page
      title="What SecuLayer can't stop"
      lead="Prompt injection isn't solved. Here is where this demo's defenses fall short, and why."
    >
      <EmptyState
        icon={BookOpen}
        title="The hard cases haven't been measured yet"
        help="Each attack SecuLayer can't reliably stop is listed here with its measured rate, once the evaluation has run."
      />
    </Page>
  );
}
