import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

const SCREENSHOTS = fileURLToPath(new URL("../../artifacts/screenshots/", import.meta.url));

/** Aborts and records every request that isn't to the local server. */
async function guardNetwork(page: Page): Promise<string[]> {
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

async function expectNoSeriousAxeViolations(page: Page) {
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

async function expectDesignBasics(page: Page) {
  const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(background).toBe("rgb(255, 255, 255)");

  const fonts = await page.evaluate(async () => {
    await document.fonts.ready;
    const loaded = [...document.fonts].filter(
      (face) =>
        face.family.replace(/["']/g, "") === "Atkinson Hyperlegible Next Variable" &&
        face.status === "loaded",
    ).length;
    return { check: document.fonts.check('17px "Atkinson Hyperlegible Next Variable"'), loaded };
  });
  expect(fonts.check).toBe(true);
  expect(fonts.loaded).toBeGreaterThan(0);

  const pills = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("*")]
      .filter((el) => {
        const style = getComputedStyle(el);
        const radius = Math.max(
          parseFloat(style.borderTopLeftRadius) || 0,
          parseFloat(style.borderBottomRightRadius) || 0,
        );
        return radius >= 9999 && el.dataset.shape !== "round";
      })
      .map((el) => `${el.tagName.toLowerCase()}.${el.className}`),
  );
  expect(pills).toEqual([]);
}

test("home: white page, Atkinson font, no pill shapes, clean axe scan, local requests only", async ({
  page,
}, testInfo) => {
  const offsite = await guardNetwork(page);
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Replay · recorded runs|Live · / })).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Watch an AI assistant get hijacked, then watch SecuLayer stop it.",
  );

  await expectDesignBasics(page);
  await expectNoSeriousAxeViolations(page);

  const width = page.viewportSize()?.width ?? 0;
  await page.screenshot({ path: `${SCREENSHOTS}m1-home-${width}.png`, fullPage: true });

  if (testInfo.project.name === "desktop-1280") {
    const toggle = page.getByRole("button", { name: "Large text" });
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator("html")).toHaveAttribute("data-text-size", "large");
    await page.mouse.move(0, 0);
    await expectDesignBasics(page);
    await expectNoSeriousAxeViolations(page);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow, "no horizontal scroll in large-text mode").toBe(false);
    await page.screenshot({ path: `${SCREENSHOTS}m1-home-1280-large.png`, fullPage: true });
  }

  expect(offsite).toEqual([]);
});

const SCREENS: [string, string][] = [
  ["/lab", "Attack Lab"],
  ["/lab/inbox", "Inbox assistant"],
  ["/how", "How SecuLayer works"],
  ["/results", "Results"],
  ["/limits", "What SecuLayer can't stop"],
  ["/sandbox", "Try your own"],
  ["/sources", "Sources"],
  ["/no-such-page", "Page not found"],
];

test("every screen loads directly (SPA fallback) with a clean axe scan", async ({ page }) => {
  const offsite = await guardNetwork(page);
  for (const [path, heading] of SCREENS) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expectNoSeriousAxeViolations(page);
  }
  expect(offsite).toEqual([]);
});

test("mode popover explains the mode", async ({ page, request }) => {
  await guardNetwork(page);
  const meta = (await (await request.get("/api/meta")).json()) as { live_available: boolean };
  await page.goto("/");
  await page.getByRole("button", { name: /Replay · recorded runs/ }).click();
  const dialog = page.getByRole("dialog", { name: "About the demo mode" });
  await expect(dialog).toContainText("Replay mode");
  await expect(dialog.getByRole("switch", { name: "Use live mode" })).toBeDisabled();
  await expect(dialog).toContainText(
    meta.live_available ? "./run.sh --live" : "Live mode needs an OpenAI key in .env.",
  );
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

test("keyboard: the skip link comes first and the nav is reachable", async ({ page }) => {
  await guardNetwork(page);
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "SecuLayer", exact: true })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Demo", exact: true })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/lab$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Attack Lab");
});
