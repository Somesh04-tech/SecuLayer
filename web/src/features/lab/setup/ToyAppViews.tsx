import { clsx } from "clsx";
import { Fingerprint, Globe, Mail, UserRound } from "lucide-react";
import { useState, type ReactNode } from "react";

import type { ReadPart, Setup, SetupArticle, SetupEmail } from "../../../api/types";
import { Chip } from "../../../components/Chip";
import { AiReadsView } from "./AiReadsView";
import { PlainText, SandboxedFrame } from "./SandboxedFrame";

/** The bordered frame around every toy app, labelled "Toy app · sandboxed". */
function ToyAppFrame({ name, children }: { name: string; children: ReactNode }) {
  return (
    <section aria-label={`${name} (toy app)`} className="rounded-card border border-border">
      <header className="flex items-center justify-between gap-4 border-b border-border px-5 py-3">
        <h3 className="text-small font-semibold text-ink">{name}</h3>
        <span className="text-caption text-ink-3">Toy app · sandboxed</span>
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

function senderName(from: string): string {
  return from.split("<")[0]?.trim() || from;
}

function Reads({ parts, label, html }: { parts: ReadPart[]; label: string; html: boolean }) {
  const note = html
    ? "This is the source code, exactly as the app passes it to the model."
    : "This is the text, exactly as the app passes it to the model.";
  return <AiReadsView parts={parts} label={label} note={note} />;
}

export function ChatView({
  setup,
  showReads,
}: {
  setup: Extract<Setup, { kind: "chat" }>;
  showReads: boolean;
}) {
  return (
    <ToyAppFrame name="Fern, the support chat">
      {showReads ? (
        <Reads parts={setup.reads} label="What the AI reads of the message" html={false} />
      ) : (
        <div className="flex flex-col items-end gap-1">
          <span className="flex items-center gap-1.5 text-caption text-user-ink">
            <UserRound size={14} strokeWidth={1.75} aria-hidden="true" />
            Customer
          </span>
          <p className="max-w-[60ch] rounded-card border border-user-border bg-user-bg px-4 py-3 text-body text-ink">
            {setup.message}
          </p>
        </div>
      )}
    </ToyAppFrame>
  );
}

function EmailPreview({ email, showReads }: { email: SetupEmail; showReads: boolean }) {
  return (
    <div className="min-w-0 space-y-3">
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-small">
        <dt className="text-ink-3">From</dt>
        <dd className="font-mono text-mono break-words text-ink">{email.from}</dd>
        <dt className="text-ink-3">Subject</dt>
        <dd className="text-ink">{email.subject}</dd>
      </dl>
      {showReads ? (
        <Reads
          parts={email.reads}
          label={`What the AI reads of "${email.subject}"`}
          html={email.format === "html"}
        />
      ) : email.format === "html" ? (
        <SandboxedFrame html={email.body} title={`Email: ${email.subject}`} className="h-72" />
      ) : (
        <PlainText text={email.body} className="max-h-72 overflow-auto" />
      )}
    </div>
  );
}

export function InboxView({
  setup,
  showReads,
}: {
  setup: Extract<Setup, { kind: "inbox" }>;
  showReads: boolean;
}) {
  const initial = setup.emails.find((e) => e.case_specific)?.id ?? setup.emails[0]?.id ?? "";
  const [openId, setOpenId] = useState(initial);
  const open = setup.emails.find((e) => e.id === openId) ?? setup.emails[0];
  return (
    <ToyAppFrame name={`Dana's inbox · ${setup.emails.length} unread`}>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]">
        <ul aria-label="Unread emails" className="space-y-1">
          {setup.emails.map((email) => {
            const active = email.id === open?.id;
            return (
              <li key={email.id}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => setOpenId(email.id)}
                  className={clsx(
                    "w-full rounded-control border-l-3 px-3 py-2 text-left transition-colors duration-(--duration-hover) ease-standard",
                    email.case_specific ? "border-outside-border" : "border-transparent",
                    active ? "bg-accent-subtle" : "hover:bg-surface-muted",
                  )}
                >
                  <span className="flex items-center gap-1.5 text-small font-semibold text-ink">
                    <Mail size={14} strokeWidth={1.75} aria-hidden="true" className="text-ink-3" />
                    {senderName(email.from)}
                  </span>
                  <span className="block text-small text-ink-2">{email.subject}</span>
                  {(email.case_specific || email.private) && (
                    <span className="mt-1 flex flex-wrap gap-1.5">
                      {email.case_specific && (
                        <Chip tone="outside" icon={Globe}>
                          Outside content
                        </Chip>
                      )}
                      {email.private && <Chip icon={Fingerprint}>Private</Chip>}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
        {open && <EmailPreview email={open} showReads={showReads} />}
      </div>
    </ToyAppFrame>
  );
}

export function BrowserView({
  setup,
  showReads,
}: {
  setup: Extract<Setup, { kind: "page" }>;
  showReads: boolean;
}) {
  return (
    <ToyAppFrame name="Dana's browser, with the assistant sidebar">
      <div className="space-y-3">
        <p className="flex h-9 items-center gap-2 rounded-control bg-surface-muted px-3 font-mono text-mono text-ink-2">
          <Globe size={14} strokeWidth={1.75} aria-hidden="true" className="shrink-0 text-ink-3" />
          <span className="sr-only">Address: </span>
          <span className="truncate">{setup.url}</span>
        </p>
        {showReads ? (
          <Reads parts={setup.reads} label="What the AI reads of the page" html />
        ) : (
          <SandboxedFrame html={setup.html} title={`Web page: ${setup.title}`} className="h-96" />
        )}
        <div className="border-t border-border pt-3">
          <p className="flex items-center gap-1.5 text-caption text-ink-3">
            <Fingerprint size={14} strokeWidth={1.75} aria-hidden="true" />
            Dana's notes · private data the assistant can see
          </p>
          <p className="mt-1 font-mono text-mono text-ink">{setup.notes}</p>
        </div>
      </div>
    </ToyAppFrame>
  );
}

function Article({ article, showReads }: { article: SetupArticle; showReads: boolean }) {
  return (
    <li
      className={clsx(
        "rounded-control border border-border border-l-3 p-4",
        article.case_specific ? "border-l-outside-border" : "border-l-border",
      )}
    >
      <h4 className="text-small font-semibold text-ink">{article.title}</h4>
      <p className="mt-1 flex flex-wrap items-center gap-2 text-caption text-ink-3">
        <span>
          {article.author} · last edited {article.edited}
        </span>
        {article.verified ? <Chip>Verified</Chip> : <Chip tone="outside">Unverified</Chip>}
        {article.case_specific && (
          <Chip tone="outside" icon={Globe}>
            Edited for this case
          </Chip>
        )}
      </p>
      <div className="mt-3">
        {showReads ? (
          <Reads
            parts={article.reads}
            label={`What the AI reads of "${article.title}"`}
            html={false}
          />
        ) : (
          <p className="text-small whitespace-pre-wrap text-ink-2">{article.body}</p>
        )}
      </div>
    </li>
  );
}

export function HelpDeskView({
  setup,
  showReads,
}: {
  setup: Extract<Setup, { kind: "helpdesk" }>;
  showReads: boolean;
}) {
  return (
    <ToyAppFrame name="Fernway HelpDesk">
      <p className="text-small text-ink-2">
        The wiki articles retrieved for this question (the top {setup.articles.length}):
      </p>
      <ul className="mt-3 space-y-3">
        {setup.articles.map((article) => (
          <Article key={article.id} article={article} showReads={showReads} />
        ))}
      </ul>
    </ToyAppFrame>
  );
}

export function ToyAppView({ setup, showReads }: { setup: Setup; showReads: boolean }) {
  switch (setup.kind) {
    case "chat":
      return <ChatView setup={setup} showReads={showReads} />;
    case "inbox":
      return <InboxView setup={setup} showReads={showReads} />;
    case "page":
      return <BrowserView setup={setup} showReads={showReads} />;
    case "helpdesk":
      return <HelpDeskView setup={setup} showReads={showReads} />;
  }
}
