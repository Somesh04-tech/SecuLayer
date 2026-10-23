import { clsx } from "clsx";
import { ChevronDown } from "lucide-react";
import { useId } from "react";

import { Code } from "../../components/Code";
import { Popover } from "../../components/Popover";
import { Switch } from "../../components/Switch";
import { Term } from "../../components/Term";
import { shortModelName, useMeta } from "./meta";

/** Shows whether the demo plays back recorded runs or calls the model live. */
export function ModeIndicator() {
  const meta = useMeta();
  const noteId = useId();

  const label =
    meta.status === "ok"
      ? meta.data.mode === "live"
        ? `Live · ${shortModelName(meta.data.models.target)}`
        : "Replay · recorded runs"
      : meta.status === "loading"
        ? "Checking mode…"
        : "Not connected";

  const trigger = (
    <button
      type="button"
      className="inline-flex h-9 shrink-0 items-center gap-2 rounded-control border border-border-control bg-page px-3 text-small font-semibold text-ink transition-colors duration-(--duration-hover) ease-standard hover:border-ink-2"
    >
      <span
        data-shape="round"
        aria-hidden="true"
        className={clsx(
          "size-2 rounded-round",
          meta.status === "ok" && meta.data.mode === "live" ? "bg-accent" : "bg-ink-3",
        )}
      />
      {label}
      <ChevronDown size={16} strokeWidth={1.75} aria-hidden="true" />
    </button>
  );

  if (meta.status !== "ok") return trigger;

  const { mode, live_available: liveAvailable, models } = meta.data;
  const model = shortModelName(models.target);

  return (
    <Popover trigger={trigger} label="About the demo mode">
      <div className="space-y-4">
        {mode === "replay" ? (
          <section className="space-y-1">
            <p className="font-semibold text-ink">Replay mode</p>
            <p>
              You're seeing <Term id="recordedRun">recorded runs</Term>: real responses from the
              model, saved earlier. SecuLayer's own checks still run live on this computer. No
              network or API key is needed.
            </p>
          </section>
        ) : (
          <section className="space-y-1">
            <p className="font-semibold text-ink">Live mode</p>
            <p>
              Each run calls the model, {model}, through OpenAI's API, so results can differ from
              one run to the next.
            </p>
          </section>
        )}
        <section className="space-y-3 border-t border-border pt-4">
          {mode === "replay" && (
            <p>
              Live mode sends each run to the model, {model}, instead of playing back a recording.
            </p>
          )}
          <Switch label="Use live mode" checked={mode === "live"} disabled describedBy={noteId} />
          <p id={noteId} className="text-ink-3">
            {!liveAvailable ? (
              <>
                Live mode needs an OpenAI key in <Code>.env</Code>.
              </>
            ) : mode === "replay" ? (
              <>
                To switch, restart the demo with <Code>./run.sh --live</Code>.
              </>
            ) : (
              <>
                To go back to replay, restart the demo with <Code>./run.sh</Code>.
              </>
            )}
          </p>
        </section>
      </div>
    </Popover>
  );
}
