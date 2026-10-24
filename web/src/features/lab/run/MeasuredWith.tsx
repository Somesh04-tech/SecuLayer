import type { CaseDetail, ScenarioDetail } from "../../../api/types";
import { measuredCase } from "../../results/format";

/**
 * The With column's measured rate, from the evaluation summary (§7.5):
 * "SecuLayer stopped this in 3 of 3 recorded runs."
 */
export function MeasuredWith({
  scenario,
  caseDetail,
}: {
  scenario: ScenarioDetail;
  caseDetail: CaseDetail;
}) {
  const result = measuredCase(scenario.measured, caseDetail.id);
  const runs = result?.configs.B;
  if (!result || !runs || runs.runs === 0) return null;
  const user = scenario.user_name;
  let text: string;
  if (result.kind === "normal") {
    const alarms = result.false_alarms ?? 0;
    text = `Done right in ${runs.hits} of ${runs.runs} recorded runs with SecuLayer; false alarm in ${alarms} of ${runs.runs}.`;
  } else if (runs.hits > 0) {
    text = `With SecuLayer, the attack still worked in ${runs.hits} of ${runs.runs} recorded runs.`;
  } else if (runs.paused > 0) {
    const stopped = runs.runs - runs.paused;
    text = `SecuLayer paused it for ${user} in ${runs.paused} of ${runs.runs} recorded runs${stopped > 0 ? ` and stopped it in the other ${stopped}` : ""}.`;
  } else {
    const stopped = runs.trials.filter((t) => t.outcome === "stopped").length;
    text =
      stopped > 0
        ? `SecuLayer stopped this in ${stopped} of ${runs.runs} recorded runs.`
        : `Not hijacked in ${runs.runs} of ${runs.runs} recorded runs with SecuLayer.`;
  }
  return (
    <p className="text-small text-ink-2 tabular-nums" data-testid="measured-with">
      {text}
    </p>
  );
}
