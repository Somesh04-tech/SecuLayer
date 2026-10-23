import { useCallback, useEffect, useState } from "react";

/** The /api/meta response. Hand-written until the generated OpenAPI types arrive. */
export interface Meta {
  version: string;
  mode: "replay" | "live";
  live_available: boolean;
  models: { target: string; compare: string; judge: string };
  classifier: { status: "present" | "missing" };
  recordings: { files: number; models: string[] };
  budget: { limit: number; used: number; remaining: number };
}

export class ApiError extends Error {
  readonly status: number | undefined;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      headers: { accept: "application/json" },
      signal: signal ?? null,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError("The server didn't respond.");
  }
  if (!response.ok) {
    throw new ApiError(`The server answered ${response.status}.`, response.status);
  }
  return (await response.json()) as T;
}

export type ApiState<T> =
  { status: "loading" } | { status: "ok"; data: T } | { status: "error"; error: Error };

/** Fetches a JSON endpoint once per path, with a retry for error states. */
export function useApi<T>(path: string): ApiState<T> & { retry: () => void } {
  const [state, setState] = useState<ApiState<T>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getJson<T>(path, controller.signal).then(
      (data) => setState({ status: "ok", data }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          error: error instanceof Error ? error : new ApiError(String(error)),
        });
      },
    );
    return () => controller.abort();
  }, [path, attempt]);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  return { ...state, retry };
}
