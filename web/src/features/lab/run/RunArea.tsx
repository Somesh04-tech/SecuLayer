import { useState } from "react";

import type { CaseDetail, ScenarioDetail } from "../../../api/types";
import { useRun } from "../useRun";
import { AnatomyPreview } from "./AnatomyPreview";
import { RunColumn, type Side } from "./RunColumn";

/**
 * The two run columns, without and with SecuLayer, and what the model received (§3.3).
 * Mount it with `key={caseId}` so a new case starts from a clean slate.
 */
export function RunArea({
  scenario,
  caseDetail,
}: {
  scenario: ScenarioDetail;
  caseDetail: CaseDetail;
}) {
  const without = useRun();
  const withSecuLayer = useRun();
  const [ranWithout, setRanWithout] = useState(false);
  const [last, setLast] = useState<Side | null>(null);

  const lastRun = last === "with" ? withSecuLayer : last === "without" ? without : null;
  const requests = lastRun?.state.requests ?? [];
  const latest = requests.at(-1);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <RunColumn
          side="without"
          run={without}
          scenario={scenario}
          caseDetail={caseDetail}
          primary={!ranWithout}
          onRun={() => {
            setRanWithout(true);
            setLast("without");
          }}
        />
        <RunColumn
          side="with"
          run={withSecuLayer}
          scenario={scenario}
          caseDetail={caseDetail}
          primary={ranWithout}
          onRun={() => setLast("with")}
        />
      </div>
      <AnatomyPreview
        messages={latest ? latest.anatomy : null}
        callCount={requests.length}
        sideLabel={last === "with" ? "With SecuLayer" : "Without SecuLayer"}
      />
    </div>
  );
}
