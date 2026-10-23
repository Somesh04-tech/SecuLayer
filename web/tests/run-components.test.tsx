import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Meta } from "../src/api/client";
import type { CaseDetail, LayerVerdict, RunEvent, ScenarioDetail } from "../src/api/types";
import { TooltipProvider } from "../src/components/Tooltip";
import { OutcomeBanner } from "../src/features/lab/run/OutcomeBanner";
import { ReplyView } from "../src/features/lab/run/ReplyView";
import { RunArea } from "../src/features/lab/run/RunArea";
import { initialRunState, reduceRun } from "../src/features/lab/useRun";
import { MetaProvider } from "../src/features/shell/meta";

function verdict(layer: LayerVerdict["layer"], action: LayerVerdict["action"]): LayerVerdict {
  return {
    type: "layer.verdict",
    layer,
    step: 0,
    action,
    reason: `${layer} ${action}`,
    findings: [],
    latency_ms: 3,
    detail: [],
  };
}

describe("reduceRun", () => {
  it("keeps the most telling verdict for a layer across steps", () => {
    let state = reduceRun(initialRunState(), verdict("hidden_text", "removed"));
    state = reduceRun(state, verdict("hidden_text", "passed"));
    const row = state.layers.hidden_text;
    expect(row.status === "done" && row.verdict.action).toBe("removed");
    expect(state.verdicts).toHaveLength(2);
  });

  it("moves through paused and finished", () => {
    let state = reduceRun(initialRunState(), {
      type: "run.paused",
      run_id: "r1",
      call_id: "c1",
      dialog: { to: ["x@y.example"], subject: "s", body: "b", highlights: [], reason: "r" },
    });
    expect(state.status).toBe("paused");
    state = reduceRun(state, {
      type: "run.finished",
      outcome: "stopped",
      banner: { title: "Safe", sentence: "stopped by the tool guard." },
      stopped_by: "tool_guard",
      checks: {},
      reply_markdown: "I didn't send the email because Dana declined.",
      actions: [],
      cost_usd: 0,
    });
    expect(state.status).toBe("finished");
    expect(state.paused).toBeUndefined();
  });

  it("marks unrecorded combinations", () => {
    const state = reduceRun(initialRunState(), {
      type: "run.error",
      message:
        "This combination of layers wasn't recorded. Reset the layers, or switch to live mode.",
      retryable: false,
    });
    expect(state.error?.notRecorded).toBe(true);
  });
});

describe("OutcomeBanner", () => {
  it("renders the outcome word, a colon and the sentence", () => {
    render(
      <OutcomeBanner
        outcome="hijacked"
        banner={{
          title: "Hijacked",
          sentence: "the assistant emailed archive@mail-backup.example.",
        }}
      />,
    );
    const banner = screen.getByTestId("outcome-banner");
    expect(banner).toHaveAttribute("data-outcome", "hijacked");
    expect(banner).toHaveTextContent(
      "Hijacked: the assistant emailed archive@mail-backup.example.",
    );
  });
});

describe("ReplyView", () => {
  it("never loads images and gives outside links no href", () => {
    const { container } = render(
      <ReplyView
        text={
          "Summary.\n\n![badge](https://pixel-cdn.example/b.png?n=Larkspur)\n\n" +
          "[full review](https://secure-login.example/fernway) and <img src=x onerror=alert(1)>"
        }
      />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByTestId("image-placeholder")).toHaveTextContent(
      "Image from pixel-cdn.example · would load automatically",
    );
    expect(container.querySelector('a[href*="secure-login"]')).toBeNull();
    expect(screen.getByTestId("inert-link")).toHaveTextContent(
      "full review (secure-login.example)",
    );
    expect(container.innerHTML).not.toContain("onerror");
  });
});

const META: Meta = {
  version: "0.1.0",
  mode: "live",
  live_available: true,
  models: { target: "gpt-5.4-mini-2026-03-17", compare: "gpt-5.4-2026-03-05", judge: "x" },
  classifier: { status: "missing" },
  recordings: { files: 0, models: [] },
  budget: { limit: 1, used: 0, remaining: 1 },
};

const SCENARIO = {
  id: "inbox",
  title: "Inbox assistant",
  user_name: "Dana",
} as unknown as ScenarioDetail;
const CASE = {
  id: "inbox.polite_invoice",
  setup: { kind: "inbox", emails: [] },
} as unknown as CaseDetail;

function ndjson(events: RunEvent[]): Response {
  return new Response(events.map((e) => JSON.stringify(e)).join("\n") + "\n", {
    status: 200,
    headers: { "content-type": "application/x-ndjson" },
  });
}

const STARTED: RunEvent = {
  type: "run.started",
  run_id: "run-1",
  case_id: "inbox.polite_invoice",
  protected: true,
  model: "gpt-5.4-mini-2026-03-17",
  mode: "live",
  trial: 1,
  trials_available: 0,
  layers: {},
};

describe("RunArea", () => {
  it("runs with SecuLayer, pauses for Dana and continues after the decision", async () => {
    const decisions: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: string, init?: RequestInit) => {
        if (path === "/api/meta") return new Response(JSON.stringify(META));
        if (path === "/api/runs") {
          return ndjson([
            STARTED,
            verdict("tool_guard", "confirm"),
            {
              type: "tool.proposed",
              call_id: "c1",
              name: "send_email",
              arguments: { to: ["billing@northwind-payments.example"], subject: "Re: invoice" },
            },
            {
              type: "run.paused",
              run_id: "run-1",
              call_id: "c1",
              dialog: {
                to: ["billing@northwind-payments.example"],
                subject: "Re: invoice",
                body: "Account ending 4417.",
                highlights: [{ text: "4417", why: "account number" }],
                reason: "Not in Dana's contacts.",
              },
            },
          ]);
        }
        decisions.push([path, JSON.parse(String(init?.body))]);
        return ndjson([
          { type: "tool.decision", call_id: "c1", action: "declined", reason: "Dana declined." },
          {
            type: "run.finished",
            outcome: "stopped",
            banner: { title: "Safe", sentence: "stopped by the tool guard. Dana declined." },
            stopped_by: "tool_guard",
            checks: {},
            reply_markdown: "I didn't send the email because Dana declined.",
            actions: [
              {
                call_id: "c1",
                name: "send_email",
                arguments: { to: ["billing@northwind-payments.example"], subject: "Re: invoice" },
                status: "declined",
              },
            ],
            cost_usd: 0,
          },
        ]);
      }),
    );
    render(
      <MetaProvider>
        <TooltipProvider>
          <RunArea scenario={SCENARIO} caseDetail={CASE} />
        </TooltipProvider>
      </MetaProvider>,
    );
    const runWith = screen.getByRole("button", { name: "Run with SecuLayer" });
    expect(screen.getByRole("button", { name: "Run without SecuLayer" })).toHaveClass("bg-accent");
    await userEvent.click(runWith);

    const dialog = await screen.findByRole("dialog", { name: "SecuLayer paused an action" });
    const column = screen.getByRole("region", { name: "With SecuLayer" });
    expect(within(column).getByText("Asked Dana")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Don't send" }));

    await waitFor(() =>
      expect(within(column).getByTestId("outcome-banner")).toHaveTextContent(
        "Safe: stopped by the tool guard. Dana declined.",
      ),
    );
    expect(decisions).toEqual([["/api/runs/run-1/decision", { approve: false }]]);
    expect(within(column).getByText("Declined")).toBeInTheDocument();
    expect(within(column).getByText("Live run")).toBeInTheDocument();
  });

  it("replays the first hijacked recorded trial and says how often the attack worked", async () => {
    const bodies: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: string, init?: RequestInit) => {
        if (path === "/api/meta") return new Response(JSON.stringify({ ...META, mode: "replay" }));
        bodies.push(JSON.parse(String(init?.body)));
        return ndjson([
          { ...STARTED, protected: false, mode: "replay", trial: 2, trials_available: 3 },
          {
            type: "run.finished",
            outcome: "hijacked",
            banner: {
              title: "Hijacked",
              sentence: "the assistant emailed archive@mail-backup.example.",
            },
            stopped_by: null,
            checks: {},
            reply_markdown: "Done.",
            actions: [],
            cost_usd: 0,
          },
        ]);
      }),
    );
    const recordedCase = {
      ...CASE,
      recorded: { trials: 3, hijacked: [2], default_trial: 2 },
    } as unknown as CaseDetail;
    render(
      <MetaProvider>
        <TooltipProvider>
          <RunArea scenario={SCENARIO} caseDetail={recordedCase} />
        </TooltipProvider>
      </MetaProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Run without SecuLayer" }));
    const column = screen.getByRole("region", { name: "Without SecuLayer" });
    await waitFor(() =>
      expect(within(column).getByTestId("recorded-count")).toHaveTextContent(
        "The attack worked in 1 of 3 recorded runs.",
      ),
    );
    expect(bodies[0]).toMatchObject({
      case_id: "inbox.polite_invoice",
      protected: false,
      trial: 2,
    });
  });
});
