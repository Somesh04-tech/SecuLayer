import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { CaseResult, ConfigResult, EvalSummary, Rate } from "../src/api/eval";
import type { CaseDetail, ScenarioDetail } from "../src/api/types";
import { TooltipProvider } from "../src/components/Tooltip";
import { MeasuredWith } from "../src/features/lab/run/MeasuredWith";
import { ResultsPage } from "../src/pages/Results";

function rate(count: number, total: number, ci: [number, number] | null = [0.1, 0.9]): Rate {
  return { count, total, rate: total ? count / total : null, ci: total ? ci : null };
}

function config(
  id: ConfigResult["id"],
  attacks: Rate,
  extra: Partial<ConfigResult> = {},
): ConfigResult {
  return {
    id,
    label: id,
    model: "gpt-5.4-mini-2026-03-17",
    protected: id !== "A" && id !== "C",
    scope: "all 56 cases × 3 trials",
    trials: 3,
    attacks,
    paused: null,
    attacks_if_approved: null,
    normal_done: null,
    usage: { input_tokens: 1, output_tokens: 1, calls: 1, cost_usd: 0 },
    ...extra,
  };
}

const hidden: CaseResult = {
  id: "inbox.hidden_forward",
  title: "The invisible footer",
  scenario: "inbox",
  kind: "attack",
  variant_of: null,
  hard_case: false,
  configs: {
    A: { hits: 1, runs: 3, paused: 0, trials: [] },
    B: {
      hits: 0,
      runs: 3,
      paused: 0,
      trials: [1, 2, 3].map((trial) => ({
        trial,
        outcome: "stopped" as const,
        success: false,
        utility: null,
        stopped_by: "hidden_text",
        success_if_approved: null,
      })),
    },
  },
  coverage: {
    hidden_text: "all",
    rules: "some",
    classifier: "none",
    judge: "all",
    tool_guard: "all",
    output_guard: "na",
  },
  false_alarms: null,
};

const SUMMARY: EvalSummary = {
  schema_version: 1,
  generated_at: "2026-10-24T10:00:00Z",
  models: {
    target: "gpt-5.4-mini-2026-03-17",
    compare: "gpt-5.4-2026-03-05",
    judge: "gpt-5.4-mini-2026-03-17",
  },
  dataset: { attack_cases: 36, primary_attacks: 12, normal_cases: 20 },
  recordings: { count: 707, first_recorded_at: null, last_recorded_at: "2026-10-24T09:00:00Z" },
  configs: [
    config("A", rate(57, 108, [0.43, 0.62]), { normal_done: rate(59, 60) }),
    config("B", rate(5, 108, [0.02, 0.1]), {
      paused: rate(2, 108),
      attacks_if_approved: rate(7, 108),
      normal_done: rate(53, 60),
    }),
    config("C", rate(11, 36)),
    config("D", rate(8, 36)),
  ],
  layers: [
    {
      id: "hidden_text",
      label: "Hidden-text cleaner",
      kind: "input",
      caught: rate(12, 108),
      note: "",
    },
    {
      id: "hardening",
      label: "Prompt hardening",
      kind: "hardening",
      caught: null,
      asr_without: rate(23, 36),
      asr_hardening_only: rate(8, 36),
      difference: 15 / 36,
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
  added_latency_ms: { median: 420, p90: 1500, n: 168 },
  token_overhead: { median: 1.6, p90: 2, n: 150 },
  cases: { [hidden.id]: hidden },
  caveats: [{ case_id: "inbox.hidden_forward", text: "A test caveat." }],
  live: {
    layer_ms: { hidden_text: { median: 2, p90: 3, n: 10 } },
    classifier: { available: false, cold_ms: null, cached_ms: null },
  },
};

function renderPage(response: Response) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <ResultsPage />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

describe("Results page", () => {
  it("shows the empty state when make eval hasn't run", async () => {
    renderPage(new Response(JSON.stringify({ detail: "No results yet." }), { status: 404 }));
    expect(await screen.findByText("No results yet.")).toBeVisible();
    expect(screen.getByText("make eval")).toBeVisible();
  });

  it("shows other errors with a retry", async () => {
    renderPage(new Response("", { status: 500 }));
    expect(await screen.findByText("Couldn't load the results.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
  });

  it("draws every configuration with its rate, denominator and interval", async () => {
    renderPage(new Response(JSON.stringify(SUMMARY), { status: 200 }));
    const without = await screen.findByTestId("bar-A");
    expect(without).toHaveTextContent("Without SecuLayer");
    expect(without).toHaveTextContent("53%");
    expect(without).toHaveTextContent("57 of 108 runs");
    expect(screen.getByTestId("bar-B")).toHaveTextContent("5 of 108 runs");
    expect(screen.getByTestId("bar-D")).toHaveTextContent("Prompt hardening only (12 attacks)");
    expect(screen.getByTestId("whisker-A")).toBeInTheDocument();
    expect(screen.getByTestId("paused")).toHaveTextContent("2 of 108 runs");
    expect(screen.getByTestId("paused")).toHaveTextContent("7 of 108 runs");
    expect(screen.getByText("Download raw results").closest("a")).toHaveAttribute(
      "href",
      "/api/eval/latest",
    );
  });

  it("shows the false alarms, layers, coverage symbols and caveats", async () => {
    renderPage(new Response(JSON.stringify(SUMMARY), { status: 200 }));
    expect(await screen.findByText("(6 of 60 runs)")).toBeVisible();
    expect(screen.getByTestId("layer-hardening")).toHaveTextContent("−42 points");
    const row = screen.getByTestId("coverage-inbox.hidden_forward");
    expect(
      within(row).getByRole("img", { name: "Cleaner: caught in every run" }),
    ).toHaveTextContent("●");
    expect(within(row).getByRole("img", { name: "Rules: caught in some runs" })).toHaveTextContent(
      "◐",
    );
    expect(within(row).getByRole("img", { name: "Classifier: missed" })).toHaveTextContent("○");
    expect(within(row).getByRole("img", { name: "Output guard: doesn't apply" })).toHaveTextContent(
      "–",
    );
    expect(row).toHaveTextContent("Worked 1 of 3");
    expect(row).toHaveTextContent("Stopped 3 of 3");
    expect(screen.getByTestId("caveats")).toHaveTextContent("A test caveat.");
    expect(screen.getByText("classifier not downloaded on this machine")).toBeVisible();
  });
});

describe("MeasuredWith", () => {
  const scenario = {
    user_name: "Dana",
    measured: { [hidden.id]: hidden },
  } as unknown as ScenarioDetail;

  it("states the protected rate with its denominator", () => {
    render(<MeasuredWith scenario={scenario} caseDetail={{ id: hidden.id } as CaseDetail} />);
    expect(screen.getByTestId("measured-with")).toHaveTextContent(
      "SecuLayer stopped this in 3 of 3 recorded runs.",
    );
  });

  it("renders nothing without measurements", () => {
    const { container } = render(
      <MeasuredWith
        scenario={{ ...scenario, measured: null } as ScenarioDetail}
        caseDetail={{ id: hidden.id } as CaseDetail}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
