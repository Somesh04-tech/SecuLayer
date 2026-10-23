import { useCallback, useEffect, useRef, useState } from "react";

import { postNdjson } from "../../api/stream";
import {
  LAYERS,
  type AttackerEvent,
  type LayerName,
  type LayerVerdict,
  type ModelRequest,
  type ModelResponse,
  type RunBody,
  type RunEvent,
  type RunFinished,
  type RunPaused,
  type RunStarted,
  type ToolDecision,
  type ToolProposed,
  type ToolResult,
} from "../../api/types";

/** Replayed events are spaced 150 ms apart so the order is visible (§3.4). */
export const REPLAY_PACE_MS = 150;

export type LayerRow =
  { status: "waiting" } | { status: "running" } | { status: "done"; verdict: LayerVerdict };

export interface ToolStep {
  proposed: ToolProposed;
  decisions: ToolDecision[];
  result?: ToolResult;
}

export interface RunState {
  status: "idle" | "running" | "paused" | "finished" | "error";
  started?: RunStarted;
  layers: Record<LayerName, LayerRow>;
  /** Every verdict in order, for the pipeline's total time. */
  verdicts: LayerVerdict[];
  /** Every event in the order it arrived, for the step-by-step timeline. */
  events: RunEvent[];
  requests: ModelRequest[];
  responses: ModelResponse[];
  tools: ToolStep[];
  attacker: AttackerEvent[];
  paused?: RunPaused | undefined;
  finished?: RunFinished;
  /** A run.error event, or the stream failing. */
  error?: { message: string; retryable: boolean; notRecorded: boolean };
  /** Calls to the model so far, for "Calling the model, 2 of 3…". */
  modelCalls: number;
}

function waitingLayers(): Record<LayerName, LayerRow> {
  return Object.fromEntries(LAYERS.map((l) => [l, { status: "waiting" }])) as Record<
    LayerName,
    LayerRow
  >;
}

export function initialRunState(): RunState {
  return {
    status: "idle",
    layers: waitingLayers(),
    verdicts: [],
    events: [],
    requests: [],
    responses: [],
    tools: [],
    attacker: [],
    modelCalls: 0,
  };
}

// The row keeps the most telling verdict across steps: an intervention beats a pass.
const WEIGHT: Record<LayerVerdict["action"], number> = {
  blocked: 6,
  withheld: 6,
  removed: 6,
  confirm: 5,
  flagged: 4,
  unavailable: 3,
  applied: 2,
  passed: 1,
  off: 0,
  not_reached: 0,
};

function keepVerdict(current: LayerRow, next: LayerVerdict): LayerRow {
  if (current.status === "done" && WEIGHT[current.verdict.action] > WEIGHT[next.action]) {
    return current;
  }
  return { status: "done", verdict: next };
}

/** Applies one run event to the state. Pure, so it is easy to test. */
export function reduceRun(previous: RunState, event: RunEvent): RunState {
  const state = { ...previous, events: [...previous.events, event] };
  switch (event.type) {
    case "run.started":
      return { ...state, status: "running", started: event };
    case "layer.started": {
      const row = state.layers[event.layer];
      if (row.status === "done") return state;
      return { ...state, layers: { ...state.layers, [event.layer]: { status: "running" } } };
    }
    case "layer.verdict":
      return {
        ...state,
        verdicts: [...state.verdicts, event],
        layers: { ...state.layers, [event.layer]: keepVerdict(state.layers[event.layer], event) },
      };
    case "model.request":
      return { ...state, requests: [...state.requests, event], modelCalls: state.modelCalls + 1 };
    case "model.response":
      return { ...state, responses: [...state.responses, event] };
    case "tool.proposed":
      return { ...state, tools: [...state.tools, { proposed: event, decisions: [] }] };
    case "tool.decision":
    case "tool.result":
      return {
        ...state,
        tools: state.tools.map((step) =>
          step.proposed.call_id !== event.call_id
            ? step
            : event.type === "tool.decision"
              ? { ...step, decisions: [...step.decisions, event] }
              : { ...step, result: event },
        ),
      };
    case "attacker.event":
      return { ...state, attacker: [...state.attacker, event] };
    case "run.paused":
      return { ...state, status: "paused", paused: event };
    case "run.error":
      return {
        ...state,
        error: {
          message: event.message,
          retryable: event.retryable,
          notRecorded: event.message.includes("wasn't recorded"),
        },
      };
    case "run.finished":
      return {
        ...state,
        status: event.outcome === "error" ? "error" : "finished",
        finished: event,
        paused: undefined,
      };
  }
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (ms <= 0 || signal.aborted) return resolve();
    const timer = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

/**
 * Runs a case and keeps its state as events stream in. `decide` answers a paused run;
 * `cancel` stops the stream; `reset` clears the column.
 */
export function useRun(options: { paceMs?: number } = {}) {
  const pace = options.paceMs ?? REPLAY_PACE_MS;
  const [state, setState] = useState<RunState>(initialRunState);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const consume = useCallback(
    async (path: string, body: unknown, fresh: boolean) => {
      controller.current?.abort();
      const abort = new AbortController();
      controller.current = abort;
      if (fresh) setState({ ...initialRunState(), status: "running" });
      else setState((s) => ({ ...s, status: "running", paused: undefined }));
      let replay = false;
      let first = true;
      try {
        for await (const event of postNdjson(path, body, abort.signal)) {
          if (abort.signal.aborted) return;
          if (event.type === "run.started") replay = event.mode === "replay";
          if (replay && !first) await sleep(pace, abort.signal);
          first = false;
          if (abort.signal.aborted) return;
          setState((s) => reduceRun(s, event));
        }
      } catch (error) {
        if (abort.signal.aborted) return;
        const message = error instanceof Error ? error.message : String(error);
        setState((s) => ({
          ...s,
          status: "error",
          error: { message, retryable: true, notRecorded: false },
        }));
      }
    },
    [pace],
  );

  const start = useCallback((body: RunBody) => consume("/api/runs", body, true), [consume]);

  const decide = useCallback(
    (approve: boolean) => {
      const runId = state.paused?.run_id;
      if (!runId) return Promise.resolve();
      return consume(`/api/runs/${encodeURIComponent(runId)}/decision`, { approve }, false);
    },
    [consume, state.paused],
  );

  const cancel = useCallback(() => {
    controller.current?.abort();
    setState((s) => (s.status === "running" ? { ...s, status: "idle" } : s));
  }, []);

  const reset = useCallback(() => {
    controller.current?.abort();
    setState(initialRunState());
  }, []);

  return { state, start, decide, cancel, reset };
}

export type RunController = ReturnType<typeof useRun>;
