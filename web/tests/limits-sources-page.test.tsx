import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { allSourceUrls } from "../src/content/sources";
import { SourcesPage } from "../src/pages/Sources";

describe("Sources page", () => {
  it("links every source, opens them in a new tab, and credits Llama", () => {
    render(
      <MemoryRouter>
        <SourcesPage />
      </MemoryRouter>,
    );
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    for (const url of allSourceUrls()) expect(hrefs).toContain(url);
    for (const link of screen.getAllByRole("link")) {
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noreferrer");
    }
    expect(screen.getByText("Built with Llama")).toBeInTheDocument();
    expect(screen.getByText("All sources were checked on 2026-10-23.")).toBeInTheDocument();
    const incidents = screen.getByRole("table");
    expect(within(incidents).getByRole("rowheader", { name: /EchoLeak/ })).toBeInTheDocument();
  });
});
