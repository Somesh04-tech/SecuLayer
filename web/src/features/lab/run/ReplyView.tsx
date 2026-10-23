import { ImageOff } from "lucide-react";
import type { ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { hostOf, isLocal } from "./labels";

/**
 * The assistant's reply as Markdown, rendered safely (§6.10): raw HTML is skipped, images
 * never load (a placeholder says where they would have loaded from), and links to other sites
 * are shown as text with their domain, never as clickable links.
 */
const components: Components = {
  img: ({ src, alt }) => {
    const url = typeof src === "string" ? src : "";
    const host = hostOf(url) || "this site";
    return (
      <span
        data-testid="image-placeholder"
        className="my-2 flex items-center gap-2 rounded-chip border border-dashed border-border-strong bg-surface-muted px-3 py-2 text-small text-ink-2"
      >
        <ImageOff size={16} strokeWidth={1.75} aria-hidden="true" className="shrink-0" />
        <span>
          Image from <span className="font-mono">{host}</span> · would load automatically
          {alt ? <span className="text-ink-3"> (“{alt}”)</span> : null}
        </span>
      </span>
    );
  },
  a: ({ href, children }) => {
    const url = typeof href === "string" ? href : "";
    if (url && isLocal(url)) {
      return (
        <a href={url} className="text-accent underline underline-offset-4">
          {children}
        </a>
      );
    }
    const host = hostOf(url);
    return (
      <span data-testid="inert-link">
        <span className="underline decoration-ink-3 decoration-dotted underline-offset-4">
          {children}
        </span>
        {host && <span className="font-mono text-small text-ink-3"> ({host})</span>}
      </span>
    );
  },
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
  h1: ({ children }) => <p className="my-2 font-bold">{children}</p>,
  h2: ({ children }) => <p className="my-2 font-bold">{children}</p>,
  h3: ({ children }) => <p className="my-2 font-semibold">{children}</p>,
  code: ({ children }) => (
    <code className="rounded-chip bg-surface-muted px-1 font-mono text-mono">{children}</code>
  ),
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-chip bg-surface-muted p-3 font-mono text-mono">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-3 border-border-strong pl-3 text-ink-2">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="text-small">{children}</table>
    </div>
  ),
};

export function ReplyMarkdown({ text }: { text: string }) {
  return (
    <div className="text-body break-words text-ink">
      <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}

export function ReplyView({ text, title }: { text: string; title?: ReactNode }) {
  return (
    <div>
      <h3 className="text-small font-semibold text-ink">{title ?? "Assistant's reply"}</h3>
      <div className="mt-2">
        {text.trim() ? (
          <ReplyMarkdown text={text} />
        ) : (
          <p className="text-small text-ink-3">No reply.</p>
        )}
      </div>
    </div>
  );
}
