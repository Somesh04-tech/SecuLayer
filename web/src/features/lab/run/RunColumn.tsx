import { LoaderCircle, Play, RotateCw, X } from "lucide-react";
import { useId, useState } from "react";

import type { ActionOut, CaseDetail, ScenarioDetail } from "../../../api/types";
import { setupOf } from "../../../api/types";
import { Button } from "../../../components/Button";
import { Code } from "../../../components/Code";
import { useMeta } from "../../shell/meta";
import type { RunController, RunState } from "../useRun";
import { ActionsList } from "./ActionsList";
import { AttackerServer } from "./AttackerServer";
import { ConfirmDialog } from "./ConfirmDialog";
import { OutcomeBanner } from "./OutcomeBanner";
import { Pipeline } from "./Pipeline";
import { ReplyView } from "./ReplyView";
import { TrialNavigator } from "./TrialNavigator";

export type Side = "without" | "with";

const COPY: Record<Side, { title: string; sub: string; button: string }> = {
  without: {
    title: "Without SecuLayer",
    sub: "The app as many are built today.",
    button: "Run without SecuLayer",
  },
  with: {
    title: "With SecuLayer",
    sub: "Same app, same model, same request.",
    button: "Run with SecuLayer",
  },
};

const THING: Record<string, string> = {
  inbox: "inbox",
  chat: "message",
  page: "page",
  helpdesk: "question",
};

/** The actions so far: the finished list, or one built from the tool events of a paused run. */
export function actionsOf(state: RunState): ActionOut[] {
  if (state.finished) return state.finished.actions;
  return state.tools.map((step) => {
    const actions = step.decisions.map((d) => d.action);
    const status: ActionOut["status"] = actions.includes("block")
      ? "blocked"
      : actions.includes("declined")
        ? "declined"
        : step.result
          ? "done"
          : actions.includes("confirm")
            ? "awaiting_approval"
            : "done";
    return {
      call_id: step.proposed.call_id,
      name: step.proposed.name,
      arguments: step.proposed.arguments,
      status,
    };
  });
}

function Skeleton() {
  return (
    <div aria-hidden="true" className="space-y-2">
      <div className="h-4 w-11/12 rounded-chip bg-surface-muted" />
      <div className="h-4 w-2/3 rounded-chip bg-surface-muted" />
    </div>
  );
}

function Notice({ children, actions }: { children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div role="status" className="rounded-card border border-border-strong px-4 py-3 text-small">
      <div className="text-ink-2">{children}</div>
      {actions && <div className="mt-3 flex flex-wrap items-center gap-3">{actions}</div>}
    </div>
  );
}

/** One run column: its button, the run's progress and outcome, the reply and actions (§4.5). */
export function RunColumn({
  side,
  run,
  scenario,
  caseDetail,
  primary,
  onRun,
}: {
  side: Side;
  run: RunController;
  scenario: ScenarioDetail;
  caseDetail: CaseDetail;
  primary: boolean;
  onRun: () => void;
}) {
  const copy = COPY[side];
  const headingId = useId();
  const meta = useMeta();
  const live = meta.status === "ok" && meta.data.mode === "live";
  const liveAvailable = meta.status === "ok" && meta.data.live_available;
  const [trial, setTrial] = useState(1);
  const { state } = run;
  const userName = scenario.user_name;
  const busy = state.status === "running";

  const start = (nextTrial: number) => {
    setTrial(nextTrial);
    onRun();
    void run.start({ case_id: caseDetail.id, protected: side === "with", trial: nextTrial });
  };

  const setupKind = setupOf(caseDetail).kind;
  const actions = actionsOf(state);
  const finished = state.finished;
  const started = state.started;

  return (
    <section
      aria-labelledby={headingId}
      className="flex min-w-0 flex-col gap-5 rounded-card border border-border p-5 xl:p-6"
    >
      <header>
        <h2 id={headingId} className="text-h3 text-ink">
          {copy.title}
        </h2>
        <p className="mt-1 text-small text-ink-2">{copy.sub}</p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant={primary ? "primary" : "secondary"}
          icon={Play}
          disabled={busy}
          onClick={() => start(1)}
        >
          {copy.button}
        </Button>
        {busy && (
          <Button variant="ghost" icon={X} onClick={run.cancel}>
            Cancel
          </Button>
        )}
        {side === "with" && <span className="text-small text-ink-3">Layers: all 5 on</span>}
      </div>

      {busy && (
        <p role="status" className="flex items-center gap-2 text-small text-ink-2">
          <LoaderCircle
            size={16}
            strokeWidth={1.75}
            aria-hidden="true"
            className="animate-spin motion-reduce:animate-none"
          />
          {live || started?.mode === "live"
            ? `Calling the model, call ${Math.max(state.modelCalls, 1)}…`
            : "Replaying a recorded run…"}
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

      {state.error &&
        (state.error.notRecorded ? (
          <Notice
            actions={
              <>
                <Button variant="secondary" size="small" disabled>
                  Switch to live mode
                </Button>
                <span className="text-ink-3">
                  {liveAvailable ? (
                    <>
                      Restart the demo with <Code>./run.sh --live</Code>.
                    </>
                  ) : (
                    <>
                      Live mode needs an OpenAI key in <Code>.env</Code>.
                    </>
                  )}
                </span>
              </>
            }
          >
            This combination of layers wasn't recorded. Reset the layers, or switch to live mode.
          </Notice>
        ) : (
          <Notice
            actions={
              <>
                <Button
                  variant="secondary"
                  size="small"
                  icon={RotateCw}
                  onClick={() => start(trial)}
                >
                  Try again
                </Button>
                {live && (
                  <>
                    <Button variant="secondary" size="small" disabled>
                      Switch to replay
                    </Button>
                    <span className="text-ink-3">
                      Restart the demo with <Code>./run.sh</Code>.
                    </span>
                  </>
                )}
              </>
            }
          >
            {state.error.message}
          </Notice>
        ))}

      {started &&
        (finished || state.status === "paused") &&
        (started.mode === "live" ? (
          <p className="text-small text-ink-2">Live run</p>
        ) : (
          <TrialNavigator
            trial={started.trial}
            available={started.trials_available}
            disabled={busy}
            onChange={start}
          />
        ))}

      {side === "with" && (
        <Pipeline layers={state.layers} verdicts={state.verdicts} userName={userName} />
      )}

      {state.status === "idle" && !state.error && (
        <p className="text-body text-ink-3">
          {side === "without"
            ? `Run it to see what the assistant does with this ${THING[setupKind] ?? "request"}.`
            : "Run it to see which of SecuLayer's checks catch this."}
        </p>
      )}

      {busy && !finished && <Skeleton />}

      {finished && finished.outcome !== "error" && (
        <>
          <ReplyView text={finished.reply_markdown} />
          <ActionsList actions={actions} />
        </>
      )}
      {!finished && state.status === "paused" && <ActionsList actions={actions} />}

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
