import { Library } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { Page } from "../components/Page";

export function SourcesPage() {
  return (
    <Page
      title="Sources"
      lead="Every incident, paper and framework this app cites, with links and dates, plus license credits."
    >
      <EmptyState
        icon={Library}
        title="No sources listed yet"
        help="The list is added together with the pages that cite it."
      />
    </Page>
  );
}
