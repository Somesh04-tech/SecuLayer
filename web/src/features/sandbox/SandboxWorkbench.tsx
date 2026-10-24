import { RotateCcw, ScanSearch, UserRound } from "lucide-react";
import { useId, useState } from "react";

import { ApiError, useApi } from "../../api/client";
import type { ScenarioDetail } from "../../api/types";
import { Button } from "../../components/Button";
import { Code } from "../../components/Code";
import { ErrorState } from "../../components/EmptyState";
import { Term } from "../../components/Term";
import { useMeta } from "../shell/meta";
import { LiveColumns } from "./LiveColumns";
import { editTarget, sandboxScenario } from "./sandboxScenarios";
import { ScreenResultView, type ScreenResult } from "./ScreenResultView";

export const MAX_TEXT = 20_000;

async function screen(body: unknown): Promise<ScreenResult> {
  let response: Response;
  try {
    response = await fetch("/api/screen", {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError("The server didn't respond.");
  }
  if (!response.ok) {
    let detail = `The server answered ${response.status}.`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      // keep the generic message
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as ScreenResult;
}

type CheckState =
  | { status: "idle" }
  | { status: "checking" }
  | { status: "done"; result: ScreenResult }
  | { status: "error"; message: string };

/** One scenario's editor, local checks and (in live mode) the two run columns. */
export function SandboxWorkbench({ scenarioId }: { scenarioId: string }) {
  const config = sandboxScenario(scenarioId);
  const detail = useApi<ScenarioDetail>(`/api/scenarios/${scenarioId}`);
  const meta = useMeta();
  const live = meta.status === "ok" && meta.data.mode === "live";
  // null until the viewer edits: the editor then shows the original attacker content.
  const [edited, setEdited] = useState<string | null>(null);
  const [check, setCheck] = useState<CheckState>({ status: "idle" });
  const editorId = useId();
  const noteId = useId();

  // A payload without cases (a broken or unexpected response) shows the error state.
  const cases = detail.status === "ok" && Array.isArray(detail.data.cases) ? detail.data.cases : [];
  const caseDetail = cases.find((c) => c.id === config.baseCase);
  const target =
    detail.status === "ok" && caseDetail ? editTarget(detail.data, caseDetail) : undefined;

  if (detail.status === "loading") {
    return <p className="text-small text-ink-3">Loading the toy app…</p>;
  }
  if (detail.status === "error" || !caseDetail || !target) {
    return (
      <ErrorState
        icon={ScanSearch}
        title="Couldn't load this toy app."
        help="The server didn't send the scenario."
        action={
          <Button variant="secondary" onClick={detail.retry}>
            Try again
          </Button>
        }
      />
    );
  }

  const scenario = detail.data;
  const text = edited ?? target.original;
  const isChat = config.as === "user";
  const changed = text !== target.original;
  const runCheck = async () => {
    setCheck({ status: "checking" });
    try {
      const result = await screen({
        scenario_id: config.id,
        text,
        as: config.as,
        format: config.format,
      });
      setCheck({ status: "done", result });
    } catch (error) {
      setCheck({
        status: "error",
        message: error instanceof Error ? error.message : String(error),
      });
    }
  };

  return (
    <div className="space-y-10">
      <section aria-labelledby="sandbox-edit" className="space-y-4">
        <h2 id="sandbox-edit" className="text-h2 text-ink">
          Your attack
        </h2>
        <p className="max-w-prose text-body text-ink-2">{target.role}</p>
        {!isChat && (
          <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-body">
            <span className="inline-flex items-center gap-1.5 text-small font-semibold text-user-ink">
              <UserRound size={16} strokeWidth={1.75} aria-hidden="true" />
              {scenario.user_name.charAt(0).toUpperCase() + scenario.user_name.slice(1)} asks:
            </span>
            <q className="rounded-chip bg-user-bg px-2 text-ink">{caseDetail.user_request}</q>
          </p>
        )}
        <div>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <label htmlFor={editorId} className="text-small font-semibold text-ink">
              {target.what}
            </label>
            <Button
              variant="ghost"
              size="small"
              icon={RotateCcw}
              disabled={!changed}
              onClick={() => {
                setEdited(null);
                setCheck({ status: "idle" });
              }}
            >
              Reset to the original
            </Button>
          </div>
          <textarea
            id={editorId}
            aria-describedby={noteId}
            value={text}
            maxLength={MAX_TEXT}
            spellCheck={false}
            rows={isChat ? 5 : 14}
            onChange={(event) => {
              setEdited(event.target.value);
              setCheck({ status: "idle" });
            }}
            className="mt-2 block w-full resize-y rounded-control border border-border-control bg-page px-4 py-3 font-mono text-mono text-ink"
          />
          <p id={noteId} className="mt-2 text-caption text-ink-3">
            {config.format === "html"
              ? "HTML, exactly as the app sends it to the model: hidden elements and comments count."
              : "Plain text."}{" "}
            {text.length.toLocaleString("en")} of {MAX_TEXT.toLocaleString("en")} characters.
          </p>
        </div>
      </section>

      <section aria-labelledby="sandbox-check" className="space-y-4">
        <h2 id="sandbox-check" className="text-h2 text-ink">
          SecuLayer's local checks
        </h2>
        <p className="max-w-prose text-body text-ink-2">
          {live
            ? "Check your text with the hidden-text cleaner and screening on their own, or run the whole app below."
            : "A new input has no recorded run, so here SecuLayer's local checks run on your text; the model needs live mode."}
        </p>
        <Button
          variant="primary"
          icon={ScanSearch}
          disabled={check.status === "checking" || !text.trim()}
          onClick={() => void runCheck()}
        >
          Check with SecuLayer
        </Button>
        <div aria-live="polite">
          {check.status === "checking" && (
            <p className="text-small text-ink-2">Checking your text…</p>
          )}
          {check.status === "error" && (
            <p role="alert" className="text-small text-ink">
              {check.message}
            </p>
          )}
          {check.status === "done" && (
            <ScreenResultView result={check.result} asUser={isChat} userName={scenario.user_name} />
          )}
        </div>
      </section>

      {live ? (
        <section aria-labelledby="sandbox-live" className="space-y-4">
          <h2 id="sandbox-live" className="text-h2 text-ink">
            Run it through the app
          </h2>
          <p className="max-w-prose text-body text-ink-2">
            Live mode: each run calls the model with your text, without and then with SecuLayer.
          </p>
          <LiveColumns scenario={scenario} caseId={caseDetail.id} text={text} />
        </section>
      ) : (
        <p className="max-w-prose text-small text-ink-3">
          To see what the model does with your text, restart the demo with{" "}
          <Code>./run.sh --live</Code>
          {meta.status === "ok" && !meta.data.live_available && (
            <>
              {" "}
              (it needs an OpenAI key in <Code>.env</Code>)
            </>
          )}
          . The <Term id="llmJudge">LLM judge</Term> also needs live mode.
        </p>
      )}
    </div>
  );
}
