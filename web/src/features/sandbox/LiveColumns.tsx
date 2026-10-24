import { LoaderCircle, Play, X } from "lucide-react";
import { useId } from "react";

import type { ScenarioDetail } from "../../api/types";
import { Button } from "../../components/Button";
import { ActionsList } from "../lab/run/ActionsList";
import { AttackerServer } from "../lab/run/AttackerServer";
import { ConfirmDialog } from "../lab/run/ConfirmDialog";
import { OutcomeBanner } from "../lab/run/OutcomeBanner";
import { Pipeline } from "../lab/run/Pipeline";
import { ReplyView } from "../lab/run/ReplyView";
import { actionsOf } from "../lab/run/RunColumn";
import { useRun } from "../lab/useRun";

type Side = "without" | "with";

const COPY: Record<Side, { title: string; sub: string; button: string }> = {
  without: {
    title: "Without SecuLayer",
    sub: "The app as many are built today.",
    button: "Run without SecuLayer",
  },
  with: {
    title: "With SecuLayer",
    sub: "Same app, same model, your text.",
    button: "Run with SecuLayer",
  },
};

function LiveColumn({
  side,
  scenario,
  caseId,
  text,
}: {
  side: Side;
  scenario: ScenarioDetail;
  caseId: string;
  text: string;
}) {
  const run = useRun();
  const { state } = run;
  const headingId = useId();
  const copy = COPY[side];
  const busy = state.status === "running";
  const finished = state.finished;
  const userName = scenario.user_name;
  const showReply = finished && finished.outcome !== "error";
  return (
    <section
      aria-labelledby={headingId}
      className="flex min-w-0 flex-col gap-5 rounded-card border border-border p-5 xl:p-6"
    >
      <header>
        <h3 id={headingId} className="text-h3 text-ink">
          {copy.title}
        </h3>
        <p className="mt-1 text-small text-ink-2">{copy.sub}</p>
      </header>
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant={side === "without" ? "primary" : "secondary"}
          icon={Play}
          disabled={busy || !text.trim()}
          onClick={() =>
            void run.start({ case_id: caseId, protected: side === "with", custom_text: text })
          }
        >
          {copy.button}
        </Button>
        {busy && (
          <Button variant="ghost" icon={X} onClick={run.cancel}>
            Cancel
          </Button>
        )}
      </div>
      {busy && (
        <p role="status" className="flex items-center gap-2 text-small text-ink-2">
          <LoaderCircle
            size={16}
            strokeWidth={1.75}
            aria-hidden="true"
            className="animate-spin motion-reduce:animate-none"
          />
          Calling the model, call {Math.max(state.modelCalls, 1)}…
        </p>
      )}
      <div aria-live="polite" className="empty:hidden">
        {finished && finished.outcome !== "error" && (
          <OutcomeBanner outcome={finished.outcome} banner={finished.banner} />
        )}
        {state.status === "paused" && state.paused && (
          <OutcomeBanner
            outcome="paused"
            banner={{
              title: "Paused",
              sentence: `SecuLayer is asking ${userName} before the assistant sends an email.`,
            }}
          />
        )}
      </div>
      {state.error && (
        <p
          role="alert"
          className="rounded-control border border-border-strong px-4 py-3 text-small text-ink"
        >
          {state.error.message}
        </p>
      )}
      {side === "with" && state.status !== "idle" && (
        <Pipeline layers={state.layers} verdicts={state.verdicts} userName={userName} />
      )}
      {showReply && <ReplyView text={finished.reply_markdown} />}
      {state.status !== "idle" && <ActionsList actions={actionsOf(state)} />}
      {state.attacker.length > 0 && <AttackerServer events={state.attacker} userName={userName} />}
      {state.paused && (
        <ConfirmDialog
          open={state.status === "paused"}
          dialog={state.paused.dialog}
          userName={userName}
          onDecide={(approve) => void run.decide(approve)}
        />
      )}
    </section>
  );
}

/** Live mode: run the viewer's text through the app both ways (POST /api/runs, custom_text). */
export function LiveColumns({
  scenario,
  caseId,
  text,
}: {
  scenario: ScenarioDetail;
  caseId: string;
  text: string;
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <LiveColumn side="without" scenario={scenario} caseId={caseId} text={text} />
      <LiveColumn side="with" scenario={scenario} caseId={caseId} text={text} />
    </div>
  );
}
