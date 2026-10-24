import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { CaseResult, EvalSummary, Rate, TrialResult } from "../src/api/eval";
import { TooltipProvider } from "../src/components/Tooltip";
import { QUOTES, sourceById } from "../src/content/sources";
import { measuredSentences } from "../src/features/limits/HardCase";
import { LimitsPage } from "../src/pages/Limits";

function rate(count: number, total: number): Rate {
  return { count, total, rate: count / total, ci: [0.1, 0.9] };
}

function trial(n: number, outcome: TrialResult["outcome"], extra: Partial<TrialResult> = {}) {
  return {
    trial: n,
    outcome,
    success: outcome === "hijacked",
    utility: null,
    stopped_by: null,
    success_if_approved: null,
    ...extra,
  };
}

function hardCase(id: string, a: number, b: CaseResult["configs"]["B"]): CaseResult {
  return {
    id,
    title: id,
    scenario: id.split(".")[0] ?? "",
    kind: "attack",
    variant_of: null,
    hard_case: true,
    configs: { A: { hits: a, runs: 3, paused: 0, trials: [] }, ...(b ? { B: b } : {}) },
    coverage: null,
    false_alarms: null,
  };
}

const SUMMARY = {
  schema_version: 1,
  generated_at: "2026-10-24T10:00:00Z",
  models: { target: "m", compare: "c", judge: "m" },
  dataset: { attack_cases: 36, primary_attacks: 12, normal_cases: 20 },
  recordings: { count: 1, first_recorded_at: null, last_recorded_at: null },
  configs: [],
  layers: [
    {
      id: "classifier",
      label: "Screening: classifier",
      kind: "input",
      caught: rate(3, 108),
      note: "",
    },
  ],
  false_alarms: {
    any: rate(6, 60),
    blocked: rate(3, 60),
    withheld: rate(3, 60),
    removed_needed: rate(0, 60),
    unneeded_confirmation: rate(0, 60),
  },
  added_latency_ms: { median: 1, p90: 1, n: 1 },
  token_overhead: { median: 1, p90: 1, n: 1 },
  cases: {
    "inbox.polite_invoice": hardCase("inbox.polite_invoice", 2, {
      hits: 0,
      runs: 3,
      paused: 2,
      trials: [
        trial(1, "stopped"),
        trial(2, "paused", { success_if_approved: true }),
        trial(3, "paused", { success_if_approved: true }),
      ],
    }),
    "helpdesk.misinformation": hardCase("helpdesk.misinformation", 3, {
      hits: 1,
      runs: 3,
      paused: 0,
      trials: [trial(1, "hijacked"), trial(2, "resisted"), trial(3, "resisted")],
    }),
  },
  caveats: [{ case_id: "helpdesk.misinformation", text: "The fake-policy check counts quotes." }],
  live: { layer_ms: {}, classifier: { available: false, cold_ms: null, cached_ms: null } },
} satisfies EvalSummary;

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "content-type": "application/json" },
      }),
    ),
  );
}

function renderPage() {
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <LimitsPage />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

describe("Limits page", () => {
  it("shows both hard cases with measured numbers and denominators", async () => {
    mockFetch(200, SUMMARY);
    renderPage();
    const invoice = await screen.findByTestId("hard-case-inbox.polite_invoice");
    expect(
      await within(invoice).findByText("Without SecuLayer, it worked in 2 of 3 recorded runs."),
    ).toBeInTheDocument();
    expect(invoice).toHaveTextContent(
      "With SecuLayer, it worked in 0 of 3, and 2 of 3 paused for Dana's approval. If she had approved, 2 of those 2 would have succeeded.",
    );
    expect(within(invoice).getByRole("link", { name: /Open in the demo/ })).toHaveAttribute(
      "href",
      "/lab/inbox?case=inbox.polite_invoice",
    );
    const policy = screen.getByTestId("hard-case-helpdesk.misinformation");
    expect(policy).toHaveTextContent("With SecuLayer, it worked in 1 of 3.");
    expect(policy).toHaveTextContent("The fake-policy check counts quotes.");
    expect(screen.getByText(/would have intervened in 3 of 108 attack runs/)).toBeInTheDocument();
  });

  it("falls back to the copy without numbers when there's no evaluation", async () => {
    mockFetch(404, { detail: "No results yet. Run make eval to measure them." });
    renderPage();
    expect(await screen.findByText(/numbers are missing/)).toBeInTheDocument();
    const invoice = screen.getByTestId("hard-case-inbox.polite_invoice");
    expect(invoice).toHaveTextContent("Not measured yet.");
    expect(invoice).not.toHaveTextContent(/of 3/);
  });

  it("links every quote to its source", async () => {
    mockFetch(404, { detail: "missing" });
    renderPage();
    await screen.findByText(/numbers are missing/);
    for (const quote of Object.values(QUOTES)) {
      const source = sourceById(quote.sourceId);
      const figure = screen.getByText(`“${quote.text}”`).closest("figure");
      expect(figure).not.toBeNull();
      const link = within(figure as HTMLElement).getByRole("link");
      expect(link).toHaveAttribute("href", source.links[0]?.url);
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noreferrer");
    }
  });

  it("phrases runs without pauses plainly", () => {
    const sentences = measuredSentences(
      hardCase("x.y", 1, { hits: 0, runs: 3, paused: 0, trials: [] }),
    );
    expect(sentences).toEqual([
      "Without SecuLayer, it worked in 1 of 3 recorded runs.",
      "With SecuLayer, it worked in 0 of 3.",
    ]);
  });
});
