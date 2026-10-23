import AxeBuilder from "@axe-core/playwright";
import { expect, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

/** Shared by the Attack Lab specs. Expected outcomes always come from the API's own replay. */

export const SCREENSHOTS = fileURLToPath(new URL("../../artifacts/screenshots/", import.meta.url));

export interface Finished {
  outcome: string;
  banner: { title: string; sentence: string };
  stopped_by: string | null;
}

export async function expectedRun(
  request: APIRequestContext,
  caseId: string,
  isProtected: boolean,
  layers?: Record<string, boolean>,
): Promise<{ finished: Finished; attacker: { destination: string }[] }> {
  const response = await request.post("/api/runs", {
    data: { case_id: caseId, protected: isProtected, ...(layers ? { layers } : {}) },
  });
  expect(response.ok()).toBe(true);
  const events = (await response.text())
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as { type: string } & Record<string, unknown>);
  const finished = events.find((e) => e.type === "run.finished") as unknown as Finished;
  expect(finished, `${caseId} replays to a finished run`).toBeTruthy();
  const attacker = events.filter((e) => e.type === "attacker.event") as unknown as {
    destination: string;
  }[];
  return { finished, attacker };
}

export async function guardNetwork(page: Page): Promise<string[]> {
  const offsite: string[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "127.0.0.1") {
      await route.continue();
    } else {
      offsite.push(url.href);
      await route.abort();
    }
  });
  return offsite;
}

export async function expectCleanAxe(page: Page) {
  // The toy apps' sandboxed iframes hold fictional email and page content, not our UI, and
  // can't run axe's script; legacy mode scans the page without opening helper pages.
  const results = await new AxeBuilder({ page })
    .setLegacyMode(true)
    .exclude("iframe[sandbox]")
    .analyze();
  const serious = results.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(" ")).join(", ")})`);
  expect(serious).toEqual([]);
}

export function column(page: Page, name: "Without SecuLayer" | "With SecuLayer"): Locator {
  return page.getByRole("region", { name, exact: true });
}

export async function expectOutcome(col: Locator, finished: Finished) {
  const banner = col.getByTestId("outcome-banner");
  await expect(banner).toBeVisible({ timeout: 20_000 });
  await expect(banner).toHaveAttribute("data-outcome", finished.outcome);
  await expect(banner).toContainText(finished.banner.title);
}
