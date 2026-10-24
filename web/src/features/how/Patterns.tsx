import { clsx } from "clsx";
import { ArrowRight } from "lucide-react";

type Tone = "trusted" | "untrusted" | "code";

interface Node {
  label: string;
  tone: Tone;
}

interface Pattern {
  name: string;
  source?: { label: string; url: string };
  idea: string;
  nodes: Node[];
  hardCases: string;
  cost: string;
}

const TONE: Record<Tone, string> = {
  trusted: "border-dev-border bg-dev-bg text-dev-ink",
  untrusted: "border-outside-border bg-outside-bg text-outside-ink",
  code: "border-border-strong bg-page text-ink-2",
};

/** Architectural patterns from §6.4: explained here, not built in this demo. */
const PATTERNS: Pattern[] = [
  {
    name: "Dual LLM",
    source: {
      label: "Willison, 2023",
      url: "https://simonwillison.net/2023/Apr/25/dual-llm-pattern/",
    },
    idea: "A privileged model that can use tools never sees untrusted text. A quarantined model reads untrusted text but has no tools. Ordinary code passes references such as $EMAIL_3 between them.",
    nodes: [
      { label: "Privileged model, has tools", tone: "trusted" },
      { label: "Code passes $EMAIL_3", tone: "code" },
      { label: "Quarantined model, reads email", tone: "untrusted" },
    ],
    hardCases:
      "The invisible footer and the polite invoice can't trigger a send: the model that decides to send never reads the email. The fake policy is still repeated, as data.",
    cost: "The privileged model can't reason about what the content says.",
  },
  {
    name: "Plan-then-execute",
    source: {
      label: "Beurer-Kellner et al., 2025",
      url: "https://arxiv.org/abs/2506.08837",
    },
    idea: "The agent fixes its plan (which tools, in what order) from the user's request before it reads any untrusted content. Content can change the data, but not the plan.",
    nodes: [
      { label: "User's request", tone: "trusted" },
      { label: "Fixed plan of tool calls", tone: "code" },
      { label: "Content fills in data only", tone: "untrusted" },
    ],
    hardCases:
      '"Summarize my email" never plans a send, so injected sends fail. "Handle anything urgent" still plans replies, so the polite invoice can still get one. SecuLayer\'s task-permission check is a small version of this.',
    cost: "Tasks whose steps depend on what the content says don't fit a fixed plan.",
  },
  {
    name: "Action-selector",
    idea: "The model may only choose from a fixed menu of actions and never sees tool output.",
    nodes: [
      { label: "User's request", tone: "trusted" },
      { label: "Model picks a menu item", tone: "code" },
      { label: "App runs it; output not shown to the model", tone: "code" },
    ],
    hardCases:
      "Nothing the attacker writes reaches the model, so none of these attacks apply. But it couldn't summarize an inbox either.",
    cost: "Very safe and very limited.",
  },
  {
    name: "LLM map-reduce",
    idea: "Each untrusted document is processed in its own isolated model call that can only return constrained output, such as yes or no or fixed fields. Code then combines the results.",
    nodes: [
      { label: "One isolated call per email", tone: "untrusted" },
      { label: "Fixed fields only", tone: "code" },
      { label: "Code combines them", tone: "code" },
    ],
    hardCases:
      "An email can't order a send or leak another email it never sees. The fake policy still returns $5,000 in its fields.",
    cost: "Answers lose nuance, and tasks need designing as fixed fields.",
  },
  {
    name: "Context-minimisation",
    idea: "Once the user's request is turned into a structured query, the original prompt is removed from later steps, so injected content has less to work with.",
    nodes: [
      { label: "User's request", tone: "trusted" },
      { label: "Structured query", tone: "code" },
      { label: "Later steps see only the query and results", tone: "untrusted" },
    ],
    hardCases:
      "It narrows what an injection can refer to, but a result that contains instructions is still read.",
    cost: "Follow-up steps can't use details from the original request.",
  },
  {
    name: "Code-then-execute (CaMeL)",
    source: {
      label: "Debenedetti et al., 2025",
      url: "https://arxiv.org/abs/2503.18813",
    },
    idea: 'The model writes a program from the trusted request. A custom interpreter tracks where every value came from and enforces rules such as "an email recipient must come from the user" before any tool runs.',
    nodes: [
      { label: "Trusted request", tone: "trusted" },
      { label: "Program written by the model", tone: "code" },
      { label: "Interpreter tracks each value's origin", tone: "code" },
    ],
    hardCases:
      "The polite invoice's billing address comes from an email, so the send is refused. SecuLayer's provenance check is a string-matching approximation of this. CaMeL solved 77% of AgentDojo tasks with provable security, against 84% undefended.",
    cost: "Building the interpreter and the policies, and some tasks it can't express.",
  },
];

function MiniFlow({ nodes, name }: { nodes: Node[]; name: string }) {
  return (
    <div
      role="img"
      aria-label={`${name}: ${nodes.map((n) => n.label).join(", then ")}`}
      className="flex items-stretch gap-1.5"
    >
      {nodes.map((node, index) => (
        <div key={node.label} className="flex min-w-0 flex-1 items-center gap-1.5">
          <div
            className={clsx(
              "flex min-h-16 flex-1 items-center rounded-control border px-2 py-1.5 text-caption",
              TONE[node.tone],
            )}
          >
            {node.label}
          </div>
          {index < nodes.length - 1 && (
            <ArrowRight
              size={16}
              strokeWidth={1.75}
              aria-hidden="true"
              className="shrink-0 text-ink-3"
            />
          )}
        </div>
      ))}
    </div>
  );
}

export function Patterns() {
  return (
    <>
      <p className="mt-2 max-w-prose text-body text-ink-2">
        SecuLayer filters and checks. These designs go further: they keep untrusted text away from
        the decisions in the first place. In the diagrams, grey boxes are trusted, amber boxes read
        outside content, and white boxes are ordinary code.
      </p>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {PATTERNS.map((pattern) => (
          <article
            key={pattern.name}
            aria-labelledby={`pattern-${pattern.name}`}
            className="rounded-card border border-border p-6"
          >
            <h3 id={`pattern-${pattern.name}`} className="text-h3 text-ink">
              {pattern.name}
            </h3>
            {pattern.source && (
              <p className="text-small text-ink-3">
                <a
                  href={pattern.source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent underline-offset-4 hover:text-accent-hover hover:underline"
                >
                  {pattern.source.label}
                </a>
              </p>
            )}
            <p className="mt-2 text-small text-ink-2">{pattern.idea}</p>
            <div className="mt-4">
              <MiniFlow nodes={pattern.nodes} name={pattern.name} />
            </div>
            <dl className="mt-4 space-y-2 text-small">
              <div>
                <dt className="font-semibold text-ink">This demo's attacks</dt>
                <dd className="text-ink-2">{pattern.hardCases}</dd>
              </div>
              <div>
                <dt className="font-semibold text-ink">The cost</dt>
                <dd className="text-ink-2">{pattern.cost}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </>
  );
}
