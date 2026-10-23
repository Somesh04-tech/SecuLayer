import { UserRound } from "lucide-react";
import { useState } from "react";

import { setupOf, type CaseDetail, type ScenarioDetail } from "../../../api/types";
import { Switch } from "../../../components/Switch";
import { ToyAppView } from "./ToyAppViews";

function asks(userName: string): string {
  const who = userName.charAt(0).toUpperCase() + userName.slice(1);
  return userName === "the customer" ? `${who} writes:` : `${who} asks:`;
}

/** "The setup": the user's request, the toy app, and the "Show what the AI reads" switch. */
export function SetupPanel({
  scenario,
  caseDetail,
}: {
  scenario: ScenarioDetail;
  caseDetail: CaseDetail;
}) {
  const [showReads, setShowReads] = useState(false);
  const setup = setupOf(caseDetail);
  return (
    <section aria-labelledby="setup-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 id="setup-heading" className="text-h2 text-ink">
          The setup
        </h2>
        <Switch label="Show what the AI reads" checked={showReads} onCheckedChange={setShowReads} />
      </div>
      {setup.kind !== "chat" && (
        <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-body">
          <span className="inline-flex items-center gap-1.5 text-small font-semibold text-user-ink">
            <UserRound size={16} strokeWidth={1.75} aria-hidden="true" />
            {asks(scenario.user_name)}
          </span>
          <q className="rounded-chip bg-user-bg px-2 text-ink">{caseDetail.user_request}</q>
        </p>
      )}
      <ToyAppView setup={setup} showReads={showReads} />
    </section>
  );
}
