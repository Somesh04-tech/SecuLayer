import { PencilLine } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { Page } from "../components/Page";

export function SandboxPage() {
  return (
    <Page
      title="Try your own"
      lead="Write the attacker's text yourself, run it, and see what SecuLayer makes of it."
    >
      <EmptyState
        icon={PencilLine}
        title="Nothing to edit yet"
        help="The sandbox uses the same toy apps as the demo, and their data hasn't been added to this build yet."
      />
    </Page>
  );
}
