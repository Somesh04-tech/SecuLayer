import { clsx } from "clsx";

/**
 * Toy-app HTML, rendered inertly (§4.5, §6.10): an iframe with an empty sandbox (no scripts,
 * no same-origin access); the page's CSP still applies, so nothing outside loads.
 */
export function SandboxedFrame({
  html,
  title,
  className,
}: {
  html: string;
  title: string;
  className?: string;
}) {
  return (
    <iframe
      sandbox=""
      srcDoc={html}
      title={title}
      referrerPolicy="no-referrer"
      className={clsx("block w-full rounded-control border border-border bg-page", className)}
    />
  );
}

/** Plain-text content (a text email, an article body), wrapped and never parsed as HTML. */
export function PlainText({ text, className }: { text: string; className?: string }) {
  return (
    <div
      className={clsx(
        "rounded-control border border-border bg-page p-4 text-small whitespace-pre-wrap text-ink",
        className,
      )}
    >
      {text}
    </div>
  );
}
