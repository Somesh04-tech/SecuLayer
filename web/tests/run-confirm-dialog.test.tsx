import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Dialog } from "../src/api/types";
import { ConfirmDialog } from "../src/features/lab/run/ConfirmDialog";

const DIALOG: Dialog = {
  to: ["billing@northwind-payments.example"],
  subject: "Re: Invoice #4471 — action needed today",
  body: "Here are the remittance details: Fernway account ending 4417.",
  highlights: [{ text: "4417", why: "The body contains Fernway's account number." }],
  reason: "billing@northwind-payments.example isn't in Dana's contacts.",
};

function renderDialog(onDecide = vi.fn()) {
  render(<ConfirmDialog open dialog={DIALOG} userName="Dana" onDecide={onDecide} />);
  return onDecide;
}

describe("ConfirmDialog", () => {
  it("shows the email and focuses Don't send", () => {
    renderDialog();
    const dialog = screen.getByRole("dialog", { name: "SecuLayer paused an action" });
    expect(dialog).toHaveTextContent("The assistant wants to send this email.");
    expect(dialog).toHaveTextContent("billing@northwind-payments.example");
    expect(dialog).toHaveTextContent("Would Dana send this?");
    expect(screen.getByText("4417").tagName).toBe("MARK");
    expect(screen.getByRole("button", { name: "Don't send" })).toHaveFocus();
  });

  it("Escape cancels the action", async () => {
    const onDecide = renderDialog();
    await userEvent.keyboard("{Escape}");
    expect(onDecide).toHaveBeenCalledExactlyOnceWith(false);
  });

  it("Don't send declines and Send anyway approves", async () => {
    const decline = renderDialog();
    await userEvent.click(screen.getByRole("button", { name: "Don't send" }));
    expect(decline).toHaveBeenCalledExactlyOnceWith(false);
  });

  it("Send anyway approves", async () => {
    const approve = renderDialog();
    await userEvent.click(screen.getByRole("button", { name: "Send anyway" }));
    expect(approve).toHaveBeenCalledExactlyOnceWith(true);
  });
});
