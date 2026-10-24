import { expect, test } from "@playwright/test";

import { expectCleanAxe, guardNetwork, SCREENSHOTS } from "./helpers";

/** The explainer pages (docs/PLAN.md §9 M8): each loads, scans clean and fits the laptop. */
const PAGES: [string, string, string][] = [
  ["/", "Watch an AI assistant get hijacked, then watch SecuLayer stop it.", "home"],
  ["/how", "How SecuLayer works", "how"],
  ["/limits", "What SecuLayer can't stop", "limits"],
  ["/sources", "Sources", "sources"],
];

for (const [path, heading, name] of PAGES) {
  test(`${name}: loads, clean axe scan, local requests only, no sideways scroll`, async ({
    page,
  }, testInfo) => {
    const offsite = await guardNetwork(page);
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await page.waitForLoadState("networkidle");
    await expectCleanAxe(page);
    const width = page.viewportSize()?.width ?? 0;
    await page.screenshot({ path: `${SCREENSHOTS}m8-${name}-${width}.png`, fullPage: true });

    if (testInfo.project.name === "desktop-1280") {
      await page.getByRole("button", { name: "Large text" }).click();
      await page.mouse.move(0, 0);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(overflow, "no horizontal scroll in large-text mode").toBe(false);
      await expectCleanAxe(page);
    }
    expect(offsite).toEqual([]);
  });
}

test("limits links to the patterns on how it works", async ({ page }) => {
  await guardNetwork(page);
  await page.goto("/limits");
  await page.locator('a[href="/how#patterns"]').first().click();
  await expect(page).toHaveURL(/\/how#patterns$/);
  await expect(page.locator("#patterns")).toBeInViewport();
});

test("sources: every link opens a new tab without a referrer", async ({ page }) => {
  await guardNetwork(page);
  await page.goto("/sources");
  const external = page.locator('main a[href^="http"]');
  expect(await external.count()).toBeGreaterThan(30);
  for (const link of await external.all()) {
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(link).toHaveAttribute("rel", /noreferrer/);
  }
  await expect(page.getByText("Built with Llama")).toBeVisible();
});
