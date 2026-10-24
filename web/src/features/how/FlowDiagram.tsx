import { clsx } from "clsx";
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Braces, Globe, UserRound } from "lucide-react";
import type { LucideIcon, LucideProps } from "lucide-react";
import { useId } from "react";

const icon: LucideProps = { size: 16, strokeWidth: 1.75, "aria-hidden": true };

const INPUTS: { label: string; icon: LucideIcon; className: string; text: string }[] = [
  {
    label: "Developer instructions",
    icon: Braces,
    className: "border-l-dev-ink bg-dev-bg text-dev-ink",
    text: "The app's own rules",
  },
  {
    label: "User",
    icon: UserRound,
    className: "border-l-user-ink bg-user-bg text-user-ink",
    text: "Dana's request",
  },
  {
    label: "Outside content",
    icon: Globe,
    className: "border-l-outside-border bg-outside-bg text-outside-ink",
    text: "Emails, pages, articles",
  },
];

export const FLOW_LAYERS = [
  { n: 1, name: "Hidden-text cleaner", job: "Removes hidden text and invisible characters" },
  { n: 2, name: "Screening", job: "Rules, classifier and LLM judge check for orders to the AI" },
  { n: 3, name: "Prompt hardening", job: "Marks outside content and adds a trust policy" },
  { n: 4, name: "Tool guard", job: "Checks each tool call before it runs" },
  { n: 5, name: "Output guard", job: "Checks the reply for leaks and outside links" },
] as const;

function Arrow({ icon: Icon, label }: { icon: LucideIcon; label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 text-ink-3">
      <Icon {...icon} />
      {label && <span className="text-center text-caption">{label}</span>}
    </div>
  );
}

/**
 * SecuLayer's request flow (§6.1), drawn as boxes and arrows: the app's labelled prompt parts,
 * the five layers, the model in the middle, and what comes out.
 */
export function FlowDiagram() {
  const descriptionId = useId();
  return (
    <figure aria-describedby={descriptionId} className="rounded-card border border-border p-6">
      <figcaption className="text-small font-semibold text-ink">
        One request through SecuLayer
      </figcaption>

      <div
        aria-hidden="true"
        className="mt-5 grid grid-cols-[10.5rem_1.5rem_minmax(0,1fr)_1.5rem_9rem] items-center gap-x-2"
      >
        {/* The app labels the parts of its prompt. */}
        <div className="space-y-2">
          <p className="text-caption text-ink-3">The app labels its prompt</p>
          {INPUTS.map((input) => (
            <div
              key={input.label}
              className={clsx("rounded-chip border-l-3 px-3 py-2", input.className)}
            >
              <p className="flex items-center gap-1.5 text-caption">
                <input.icon {...icon} />
                {input.label}
              </p>
              <p className="mt-0.5 text-caption text-ink-2">{input.text}</p>
            </div>
          ))}
        </div>
        <Arrow icon={ArrowRight} />

        {/* SecuLayer: five layers, the model between layers 3 and 4. */}
        <div className="rounded-control bg-surface-muted p-4">
          <p className="text-caption text-ink-3">SecuLayer</p>
          <ol className="mt-2 grid grid-cols-5 gap-2">
            {FLOW_LAYERS.map((layer) => (
              <li
                key={layer.n}
                className={clsx(
                  "flex min-h-28 flex-col rounded-control border bg-page px-3 py-2",
                  layer.n <= 3 ? "border-border-strong" : "border-ink-3",
                )}
              >
                <span className="text-caption text-ink-3">Layer {layer.n}</span>
                <span className="text-small font-semibold text-ink">{layer.name}</span>
                <span className="mt-1 text-caption text-ink-2">{layer.job}</span>
              </li>
            ))}
          </ol>
          <div className="mt-2 grid grid-cols-5 gap-2">
            <div className="col-span-2 flex items-center gap-1.5 text-caption text-ink-2">
              <ArrowLeft {...icon} className="shrink-0 text-ink-3" />
              Tool results are outside content: they pass layers 1–3 again
            </div>
            <Arrow icon={ArrowDown} label="hardened prompt" />
            <Arrow icon={ArrowUp} label="tool calls and the reply" />
            <div />
          </div>
          <div className="mt-2 grid grid-cols-5 gap-2">
            <div className="col-span-2" />
            <div className="col-span-2 rounded-control border border-ink bg-page px-3 py-2 text-center">
              <span className="text-small font-semibold text-ink">The model</span>
              <span className="block text-caption text-ink-2">reads everything as one text</span>
            </div>
            <div />
          </div>
        </div>
        <Arrow icon={ArrowRight} />

        <div className="space-y-2">
          <p className="text-caption text-ink-3">What comes out</p>
          <div className="rounded-control border border-border px-3 py-2 text-caption text-ink-2">
            <span className="block text-small font-semibold text-ink">The reply</span>
            shown after the output guard
          </div>
          <div className="rounded-control border border-border px-3 py-2 text-caption text-ink-2">
            <span className="block text-small font-semibold text-ink">Tool calls</span>
            run only if the tool guard allows, or the user approves
          </div>
        </div>
      </div>

      <div id={descriptionId} className="mt-5 max-w-prose text-small text-ink-2">
        <p>In order:</p>
        <ol className="mt-1 list-decimal space-y-0.5 pl-5">
          <li>
            The app hands SecuLayer its prompt as labelled parts: developer instructions, the user's
            request and outside content.
          </li>
          <li>
            Layers 1 to 3 clean, screen and mark the user's request and the outside content before
            the model reads them.
          </li>
          <li>
            The model answers or asks to call a tool. Layer 4 checks each tool call; a tool's result
            is outside content, so it goes back through layers 1 to 3.
          </li>
          <li>Layer 5 checks the final reply before it is shown.</li>
        </ol>
      </div>
    </figure>
  );
}
