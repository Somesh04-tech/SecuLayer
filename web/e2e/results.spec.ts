import { expect, test } from "@playwright/test";

import { expectCleanAxe, guardNetwork, SCREENSHOTS } from "./helpers";

/**
 * The Results page (docs/PLAN.md §7.5, §9 M7). Every number shown is compared with the
 * API's own summary, never hard-coded.
 */

interface Rate {
  count: number;
  total: number;
}
interface Summary {
  configs: { id: string; attacks: Rate | null }[];
  false_alarms: { any: Rate };
  cases: Record<string, { kind: string; variant_of: string | null }>;
}

test("results: every configuration's rate with its denominator, the matrix, axe", async ({
  page,
  request,
}) => {
  const response = await request.get("/api/eval/latest");
  test.skip(response.status() === 404, "make eval hasn't written data/eval/latest.json");
  const summary = (await response.json()) as Summary;
  const offsite = await guardNetwork(page);

  await page.goto("/results");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Results");
  await expect(page.getByRole("heading", { name: "Attacks that worked" })).toBeVisible();
  for (const config of summary.configs) {
    if (!config.attacks) continue;
    await expect(page.getByTestId(`bar-${config.id}`)).toContainText(
      `${config.attacks.count} of ${config.attacks.total} runs`,
    );
  }
  await expect(
    page.getByText(`(${summary.false_alarms.any.count} of ${summary.false_alarms.any.total} runs)`),
  ).toBeVisible();

  const primaries = Object.entries(summary.cases).filter(
    ([, c]) => c.kind === "attack" && c.variant_of === null,
  );
  await expect(page.locator('[data-testid^="coverage-"]')).toHaveCount(primaries.length);
  await expect(page.getByRole("link", { name: "Download raw results" })).toHaveAttribute(
    "href",
    "/api/eval/latest",
  );

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(overflow, "no horizontal page scroll").toBe(false);
  await expectCleanAxe(page);
  const width = page.viewportSize()?.width ?? 0;
  await page.screenshot({ path: `${SCREENSHOTS}m7-results-${width}.png`, fullPage: true });
  expect(offsite).toEqual([]);
});

test("results: the empty state when there is no evaluation yet", async ({ page }) => {
  await guardNetwork(page);
  await page.route("**/api/eval/latest", (route) =>
    route.fulfill({
      status: 404,
      json: { detail: "No results yet. Run make eval to measure them." },
    }),
  );
  await page.goto("/results");
  await expect(page.getByText("No results yet.")).toBeVisible();
  await expect(page.getByText("make eval")).toBeVisible();
  await expectCleanAxe(page);
});
