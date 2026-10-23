import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Meta } from "../src/api/client";
import { AppRoutes } from "../src/App";

const META: Meta = {
  version: "0.1.0",
  mode: "replay",
  live_available: false,
  models: {
    target: "gpt-5.4-mini-2026-03-17",
    compare: "gpt-5.4-2026-03-05",
    judge: "gpt-5.4-mini-2026-03-17",
  },
  classifier: { status: "missing" },
  recordings: { files: 0, models: [] },
  budget: { limit: 1_500_000, used: 0, remaining: 1_500_000 },
};

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function serveMeta(meta: Meta = META) {
  const fetchMock = vi.fn(async () => jsonResponse(meta));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderAt(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  beforeEach(() => {
    serveMeta();
  });

  it("renders the top bar, the home page and the footer", async () => {
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Main" });
    for (const label of ["Demo", "How it works", "Results", "Limits", "Try your own"]) {
      expect(within(nav).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: "SecuLayer" })).toHaveAttribute("href", "/");
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Watch an AI assistant get hijacked, then watch SecuLayer stop it.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Everything here is a sandbox with fake data. Nothing leaves this computer.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sources" })).toHaveAttribute("href", "/sources");
    expect(await screen.findByRole("button", { name: /Replay · recorded runs/ })).toBeVisible();
  });

  it("reads the mode from /api/meta and shows the live model name", async () => {
    const fetchMock = serveMeta({ ...META, mode: "live", live_available: true });
    renderAt("/");
    expect(await screen.findByRole("button", { name: /Live · gpt-5\.4-mini$/ })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith("/api/meta", expect.anything());
  });

  it("explains that live mode needs a key when none is configured", async () => {
    const user = userEvent.setup();
    renderAt("/");
    await user.click(await screen.findByRole("button", { name: /Replay · recorded runs/ }));
    const dialog = await screen.findByRole("dialog", { name: "About the demo mode" });
    expect(within(dialog).getByText(/Live mode needs an OpenAI key in/)).toBeVisible();
    expect(within(dialog).getByRole("switch", { name: "Use live mode" })).toBeDisabled();
  });

  it("shows the server-unreachable state and recovers on retry", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    renderAt("/results");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Can't reach the SecuLayer server.");
    expect(alert).toHaveTextContent("Is ./run.sh still running?");
    expect(screen.queryByRole("heading", { name: "Results" })).not.toBeInTheDocument();

    serveMeta();
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Results" })).toBeVisible();
  });

  it("toggles large text and remembers the choice", async () => {
    const user = userEvent.setup();
    renderAt("/");
    const toggle = screen.getByRole("button", { name: "Large text" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.dataset.textSize).toBe("large");
    expect(window.localStorage.getItem("seculayer.textSize")).toBe("large");

    await user.click(toggle);
    expect(document.documentElement.dataset.textSize).toBe("normal");
  });

  it("still toggles large text when storage throws", async () => {
    const user = userEvent.setup();
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    renderAt("/");
    const toggle = screen.getByRole("button", { name: "Large text" });
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.dataset.textSize).toBe("large");
  });

  it.each([
    ["/lab", "Attack Lab"],
    ["/lab/inbox", "Attack Lab"],
    ["/how", "How SecuLayer works"],
    ["/results", "Results"],
    ["/limits", "What SecuLayer can't stop"],
    ["/sandbox", "Try your own"],
    ["/sources", "Sources"],
    ["/no-such-page", "Page not found"],
  ])("routes %s to its page", async (path, heading) => {
    renderAt(path);
    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeVisible();
  });

  it("marks the current section in the nav", () => {
    renderAt("/lab/inbox");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Demo" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Results" })).not.toHaveAttribute("aria-current");
  });
});
