import { ApiError } from "./client";
import type { RunEvent } from "./types";

async function readError(response: Response): Promise<ApiError> {
  let detail = `The server answered ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    // Not JSON: keep the generic message.
  }
  return new ApiError(detail, response.status);
}

/**
 * POSTs JSON and yields the newline-delimited JSON events the server streams back
 * (application/x-ndjson, docs/PLAN.md §6.9). Stops when the stream ends or `signal` aborts.
 */
export async function* postNdjson(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<RunEvent> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/x-ndjson" },
      body: JSON.stringify(body),
      signal: signal ?? null,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError("The server didn't respond.");
  }
  if (!response.ok) throw await readError(response);
  if (!response.body) throw new ApiError("The server sent an empty response.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let newline = buffer.indexOf("\n");
      while (newline >= 0) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        if (line) yield JSON.parse(line) as RunEvent;
        newline = buffer.indexOf("\n");
      }
      if (done) break;
    }
    const rest = buffer.trim();
    if (rest) yield JSON.parse(rest) as RunEvent;
  } finally {
    reader.releaseLock();
  }
}
