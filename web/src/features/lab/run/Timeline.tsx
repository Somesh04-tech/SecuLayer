import { Disclosure } from "../../../components/Disclosure";
import { LAYER_LABELS, type RunEvent } from "../../../api/types";

export interface TimelineEntry {
  /** Seconds since the run started, summed from the layers' and the model's own timings. */
  at: number;
  text: string;
}

function shorten(text: string, max = 90): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max - 1)}…` : flat;
}

function argumentSummary(args: Record<string, unknown>): string {
  const to = args["to"];
  if (Array.isArray(to) && to.length > 0) return `to: ${to.join(", ")}, …`;
  return Object.keys(args).length > 0 ? "…" : "";
}

/** The run's events as the timeline's lines (§3.3, "Step-by-step timeline"). */
export function timelineEntries(
  events: RunEvent[],
  userName: string,
  userRequest: string,
): TimelineEntry[] {
  const entries: TimelineEntry[] = [];
  let elapsedMs = 0;
  const add = (text: string) => entries.push({ at: elapsedMs / 1000, text });
  for (const event of events) {
    switch (event.type) {
      case "run.started":
        add(`${userName}'s request received: “${shorten(userRequest)}”`);
        break;
      case "layer.verdict":
        elapsedMs += event.latency_ms;
        if (event.action !== "off" && event.action !== "not_reached") {
          add(`${LAYER_LABELS[event.layer]}: ${shorten(event.reason)}`);
        }
        break;
      case "model.response": {
        elapsedMs += event.latency_ms;
        const calls = event.tool_calls.map((c) => `${c.name}(${argumentSummary(c.arguments)})`);
        add(
          calls.length > 0
            ? `Model call ${event.call_index + 1} → asked to run ${calls.join(", ")}`
            : `Model call ${event.call_index + 1} → wrote the reply`,
        );
        break;
      }
      case "tool.result":
        add(`Tool result: ${shorten(event.summary)}`);
        break;
      case "tool.decision":
        if (event.action === "approved" || event.action === "declined") {
          add(`${userName} ${event.action} the action`);
        }
        break;
      case "run.paused":
        add(`Paused for ${userName}'s approval`);
        break;
      case "attacker.event":
        add(`The attacker's server received data (${event.channel})`);
        break;
      case "run.finished":
        if (event.outcome !== "error") add(`Done: ${event.banner.title}`);
        break;
      default:
        break;
    }
  }
  return entries;
}

/** A collapsed, step-by-step account of what happened in the run, with times. */
export function Timeline({
  events,
  userName,
  userRequest,
}: {
  events: RunEvent[];
  userName: string;
  userRequest: string;
}) {
  const entries = timelineEntries(events, userName, userRequest);
  if (entries.length === 0) return null;
  return (
    <Disclosure title="Step-by-step timeline">
      <ol className="space-y-1.5 text-small text-ink-2" data-testid="timeline">
        {entries.map((entry, index) => (
          <li key={index} className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
            <span className="text-ink-3 tabular-nums">{entry.at.toFixed(2)} s</span>
            <span className="min-w-0 break-words">{entry.text}</span>
          </li>
        ))}
      </ol>
    </Disclosure>
  );
}
