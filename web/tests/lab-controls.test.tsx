import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import type { RunEvent } from "../src/api/types";
import { TooltipProvider } from "../src/components/Tooltip";
import { isTyping, usePresenterShortcuts } from "../src/features/lab/PresenterShortcuts";
import {
  ALL_ON,
  LayerMenu,
  layerSummary,
  type LayerSettings,
} from "../src/features/lab/run/LayerMenu";
import { timelineEntries } from "../src/features/lab/run/Timeline";

function Menu() {
  const [layers, setLayers] = useState<LayerSettings>(ALL_ON);
  return (
    <TooltipProvider>
      <LayerMenu layers={layers} onChange={setLayers} />
    </TooltipProvider>
  );
}

describe("LayerMenu", () => {
  it("switches layers off, says how many are on, and resets", async () => {
    render(<Menu />);
    const trigger = screen.getByRole("button", { name: "Layers: all 5 on" });
    await userEvent.click(trigger);
    await userEvent.click(screen.getByRole("switch", { name: "Hidden-text cleaner" }));
    await userEvent.click(screen.getByRole("switch", { name: "Screening" }));
    expect(screen.getByTestId("layer-menu")).toHaveTextContent("Layers: 3 of 5 on");
    await userEvent.click(screen.getByRole("button", { name: "Reset to all on" }));
    expect(screen.getByTestId("layer-menu")).toHaveTextContent("Layers: all 5 on");
    expect(screen.getByRole("switch", { name: "Screening" })).toBeChecked();
  });

  it("summarises the switches", () => {
    expect(layerSummary({ ...ALL_ON, tool_guard: false })).toBe("Layers: 4 of 5 on");
  });
});

describe("timelineEntries", () => {
  it("lists the steps with times summed from the layers and the model", () => {
    const events = [
      {
        type: "run.started",
        run_id: "r",
        case_id: "inbox.polite_invoice",
        protected: true,
        model: "m",
        mode: "replay",
        trial: 1,
        trials_available: 1,
        layers: {},
      },
      {
        type: "model.response",
        call_index: 0,
        output_text: "",
        tool_calls: [{ call_id: "c0", name: "list_unread_emails", arguments: {} }],
        latency_ms: 610,
        usage: { input_tokens: 1, output_tokens: 1 },
        recorded: true,
        recorded_at: null,
        trial: 1,
      },
      { type: "tool.result", call_id: "c0", summary: "Listed 5 unread emails" },
      {
        type: "layer.verdict",
        layer: "hidden_text",
        step: 1,
        action: "passed",
        reason: "Nothing hidden.",
        findings: [],
        latency_ms: 10,
      },
      {
        type: "layer.verdict",
        layer: "screening",
        step: 1,
        action: "off",
        reason: "Switched off.",
        findings: [],
        latency_ms: 0,
      },
      {
        type: "model.response",
        call_index: 1,
        output_text: "",
        tool_calls: [
          {
            call_id: "c1",
            name: "send_email",
            arguments: { to: ["billing@northwind-payments.example"] },
          },
        ],
        latency_ms: 670,
        usage: { input_tokens: 1, output_tokens: 1 },
        recorded: true,
        recorded_at: null,
        trial: 1,
      },
      {
        type: "run.paused",
        run_id: "r",
        call_id: "c1",
        dialog: { to: [], subject: "", body: "", highlights: [], reason: "" },
      },
    ] as unknown as RunEvent[];
    expect(timelineEntries(events, "Dana", "Go through my unread emails.")).toEqual([
      { at: 0, text: "Dana's request received: “Go through my unread emails.”" },
      { at: 0.61, text: "Model call 1 → asked to run list_unread_emails()" },
      { at: 0.61, text: "Tool result: Listed 5 unread emails" },
      { at: 0.62, text: "Hidden-text cleaner: Nothing hidden." },
      {
        at: 1.29,
        text: "Model call 2 → asked to run send_email(to: billing@northwind-payments.example, …)",
      },
      { at: 1.29, text: "Paused for Dana's approval" },
    ]);
  });
});

function Shortcuts({ actions }: { actions: Parameters<typeof usePresenterShortcuts>[0] }) {
  const { helpOpen } = usePresenterShortcuts(actions);
  return (
    <div>
      <input aria-label="A field" />
      {helpOpen && <p>Help is open</p>}
    </div>
  );
}

describe("presenter shortcuts", () => {
  it("map keys to actions, and ignore typing and modifier keys", () => {
    const actions = { previous: vi.fn(), next: vi.fn(), run: vi.fn(), prompt: vi.fn() };
    render(<Shortcuts actions={actions} />);
    fireEvent.keyDown(window, { key: "]" });
    fireEvent.keyDown(window, { key: "[" });
    fireEvent.keyDown(window, { key: "u" });
    fireEvent.keyDown(window, { key: "s" });
    fireEvent.keyDown(window, { key: "p" });
    fireEvent.keyDown(window, { key: "s", ctrlKey: true });
    fireEvent.keyDown(screen.getByRole("textbox", { name: "A field" }), { key: "u" });
    expect(actions.next).toHaveBeenCalledTimes(1);
    expect(actions.previous).toHaveBeenCalledTimes(1);
    expect(actions.run.mock.calls).toEqual([["without"], ["with"]]);
    expect(actions.prompt).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(window, { key: "?" });
    expect(screen.getByText("Help is open")).toBeInTheDocument();
  });

  it("knows a text field from the page", () => {
    const input = document.createElement("input");
    expect(isTyping(input)).toBe(true);
    expect(isTyping(document.body)).toBe(false);
  });
});
