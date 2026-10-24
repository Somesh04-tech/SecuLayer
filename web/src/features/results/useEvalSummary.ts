import { useCallback, useEffect, useState } from "react";

import { ApiError, getJson } from "../../api/client";
import type { EvalSummary } from "../../api/eval";

export type EvalState =
  | { status: "loading" }
  | { status: "ok"; data: EvalSummary }
  | { status: "missing" }
  | { status: "error"; error: Error };

/** A light shape check, so an old or foreign file shows an error instead of breaking the page. */
function isSummary(data: unknown): data is EvalSummary {
  if (typeof data !== "object" || data === null) return false;
  const value = data as Partial<EvalSummary>;
  return (
    value.schema_version === 1 &&
    Array.isArray(value.configs) &&
    Array.isArray(value.layers) &&
    typeof value.cases === "object" &&
    value.cases !== null
  );
}

/** GET /api/eval/latest. A 404 means `make eval` hasn't run yet, not an error. */
export function useEvalSummary(): EvalState & { retry: () => void } {
  const [state, setState] = useState<EvalState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getJson<EvalSummary>("/api/eval/latest", controller.signal).then(
      (data) => {
        if (!isSummary(data)) {
          setState({
            status: "error",
            error: new ApiError(
              "The results file is in an unexpected format. Run make eval again.",
            ),
          });
          return;
        }
        setState({ status: "ok", data });
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 404) {
          setState({ status: "missing" });
          return;
        }
        setState({
          status: "error",
          error: error instanceof Error ? error : new ApiError(String(error)),
        });
      },
    );
    return () => controller.abort();
  }, [attempt]);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  return { ...state, retry };
}
