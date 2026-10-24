import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { EvalSummary, Rate } from "../src/api/eval";
import { TooltipProvider } from "../src/components/Tooltip";
import { NextSteps } from "../src/features/home/NextSteps";
import { HowItWorksPage } from "../src/pages/HowItWorks";

function rate(count: number, total: number): Rate {
  return { count, total, rate: count / total, ci: [0.1, 0.9] };
}

const SUMMARY = {
  schema_version: 1,
  generated_at: "2026-10-24T10:00:00Z",
  models: { target: "m", compare: "c", judge: "m" },
  dataset: { attack_cases: 36, primary_attacks: 12, normal_cases: 20 },
  recordings: { count: 1, first_recorded_at: null, last_recorded_at: null },
  configs: [
    { id: "A", attacks: rate(57, 108) },
    { id: "B", attacks: rate(5, 108) },
  ],
  layers: [
    {
      id: "hidden_text",
      label: "Hidden-text cleaner",
      kind: "input",
      caught: rate(24, 108),
      note: "Cleaner note.",
    },
    {
      id: "rules",
      label: "Screening: rules",
      kind: "input",
      caught: rate(36, 108),
      note: "Rules note.",
    },
    {
      id: "classifier",
      label: "Screening: classifier",
      kind: "input",
      caught: rate(3, 108),
      note: "Classifier note.",
    },
    {
      id: "judge",
      label: "Screening: LLM judge",
      kind: "input",
      caught: rate(45, 108),
      note: "Judge note.",
    },
    {
      id: "hardening",
      label: "Prompt hardening",
      kind: "hardening",
      caught: null,
      asr_without: rate(22, 36),
      asr_hardening_only: rate(8, 36),
      difference: 0.39,
      note: "Hardening note.",
    },
    {
      id: "tool_guard",
      label: "Tool guard",
      kind: "action",
      caught: rate(15, 15),
      note: "Tool note.",
    },
    {
      id: "output_guard",
      label: "Output guard",
      kind: "action",
      caught: rate(34, 42),
      note: "Output note.",
    },
  ],
  cases: {},
} as unknown as EvalSummary;

function stub(response: Response) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
}

function renderWithShell(node: React.ReactNode) {
  return render(
    <MemoryRouter>
      <TooltipProvider>{node}</TooltipProvider>
    </MemoryRouter>,
  );
}

const ok = () => new Response(JSON.stringify(SUMMARY), { status: 200 });
const missing = () => new Response(JSON.stringify({ detail: "No results yet." }), { status: 404 });

describe("How it works", () => {
  it("shows the flow figure with a text description and the five layer cards", async () => {
    stub(missing());
    renderWithShell(<HowItWorksPage />);
    const figure = screen.getByRole("figure");
    const descriptionId = figure.getAttribute("aria-describedby");
    expect(descriptionId).toBeTruthy();
    expect(document.getElementById(descriptionId!)).toHaveTextContent(
      "Layers 1 to 3 clean, screen and mark",
    );
    for (const name of [
      "Hidden-text cleaner",
      "Screening",
      "Prompt hardening",
      "Tool guard",
      "Output guard",
    ]) {
      expect(screen.getByRole("heading", { level: 3, name: new RegExp(name) })).toBeVisible();
    }
    expect(await screen.findAllByText(/Run/)).not.toHaveLength(0);
    expect(screen.getAllByText("make eval")).toHaveLength(5);
  });

  it("shows what each layer caught, with denominators", async () => {
    stub(ok());
    renderWithShell(<HowItWorksPage />);
    const cleaner = screen
      .getByRole("heading", { level: 3, name: /Hidden-text cleaner/ })
      .closest("article")!;
    expect(await within(cleaner).findByText("22% (24 of 108 runs)")).toBeVisible();
    const screening = screen
      .getByRole("heading", { level: 3, name: /Screening/ })
      .closest("article")!;
    expect(within(screening).getByText("42% (45 of 108 runs)")).toBeVisible();
    const hardening = screen
      .getByRole("heading", { level: 3, name: /Prompt hardening/ })
      .closest("article")!;
    expect(within(hardening).getByText("22 of 36 runs")).toBeVisible();
    expect(within(hardening).getByText("8 of 36 runs")).toBeVisible();
    expect(screen.getByRole("link", { name: /The polite invoice/ })).toHaveAttribute(
      "href",
      "/lab/inbox?case=inbox.polite_invoice",
    );
  });

  it("explains the six patterns with their sources", () => {
    stub(missing());
    renderWithShell(<HowItWorksPage />);
    for (const name of [
      "Dual LLM",
      "Plan-then-execute",
      "Action-selector",
      "LLM map-reduce",
      "Context-minimisation",
      "Code-then-execute (CaMeL)",
    ]) {
      expect(screen.getByRole("heading", { level: 3, name })).toBeVisible();
    }
    expect(screen.getByRole("link", { name: "Willison, 2023" })).toHaveAttribute(
      "href",
      "https://simonwillison.net/2023/Apr/25/dual-llm-pattern/",
    );
    expect(screen.getByRole("img", { name: /Dual LLM: Privileged model/ })).toBeVisible();
  });
});

describe("Home's next steps", () => {
  it("shows the measured headline with denominators", async () => {
    stub(ok());
    renderWithShell(<NextSteps />);
    expect(await screen.findByText("53% (57 of 108 runs)")).toBeVisible();
    expect(screen.getByText("5% (5 of 108 runs)")).toBeVisible();
    expect(screen.getByRole("link", { name: "Measured results" })).toHaveAttribute(
      "href",
      "/results",
    );
  });

  it("falls back to plain text before the evaluation has run", async () => {
    stub(missing());
    renderWithShell(<NextSteps />);
    expect(await screen.findByText(/measured on recorded runs/)).toBeVisible();
    expect(screen.getByRole("link", { name: "What it can't stop" })).toHaveAttribute(
      "href",
      "/limits",
    );
  });
});
