import { ChartColumn } from "lucide-react";

import { Code } from "../components/Code";
import { EmptyState } from "../components/EmptyState";
import { Page } from "../components/Page";

export function ResultsPage() {
  return (
    <Page
      title="Results"
      lead="Measured on recorded runs: how often attacks worked with and without SecuLayer, how often it blocked normal tasks, and how much time it added."
    >
      <EmptyState
        icon={ChartColumn}
        title="No results yet."
        help={
          <>
            Run <Code>make eval</Code> to measure them.
          </>
        }
      />
    </Page>
  );
}
