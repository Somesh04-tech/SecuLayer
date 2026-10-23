import { expect, test, type Locator, type Page } from "@playwright/test";

import {
  SCREENSHOTS,
  column,
  expectCleanAxe,
  expectOutcome,
  expectedRun,
  guardNetwork,
} from "./helpers";

/**
 * The mechanism (docs/PLAN.md §9 M5): the prompt anatomy, the Layers menu, the not-recorded
 * state and the presenter shortcuts. Expected outcomes come from the API's replay.
 */

const NO_CLEANER_NO_SCREENING = {
  hidden_text: false,
  screening: false,
  hardening: true,
  tool_guard: true,
  output_guard: true,
};

function anatomy(page: Page): Locator {
  return page.locator("#prompt-anatomy");
}

async function setLayers(page: Page, off: string[]) {
  await page.getByTestId("layer-menu").click();
  const menu = page.getByRole("dialog", { name: "SecuLayer's layers" });
  for (const name of off) await menu.getByRole("switch", { name }).click();
  await page.keyboard.press("Escape");
  await expect(menu).toBeHidden();
}

test("the prompt anatomy shows the attacker's text, then SecuLayer's additions", async ({
  page,
  request,
}) => {
  const offsite = await guardNetwork(page);
  const without = await expectedRun(request, "inbox.hidden_forward", false);
  const withLayer = await expectedRun(request, "inbox.hidden_forward", true);
  await page.goto("/lab/inbox?case=inbox.hidden_forward");

  await page.getByRole("button", { name: "Run without SecuLayer" }).click();
  await expectOutcome(column(page, "Without SecuLayer"), without.finished);
  const panel = anatomy(page).getByRole("tabpanel");
  await expect(anatomy(page).getByRole("tab", { name: "Without SecuLayer" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  const injected = panel.locator('[data-source="injected"]').first();
  await expect(injected).toBeVisible();
  await expect(injected).toHaveClass(/text-danger-ink/);
  await expect(panel.getByTestId("share")).toContainText("outside content");

  await page.getByRole("button", { name: "Run with SecuLayer" }).click();
  await expectOutcome(column(page, "With SecuLayer"), withLayer.finished);
  await anatomy(page).getByRole("tab", { name: "With SecuLayer" }).click();
  const added = panel.locator('[data-source="seculayer"]');
  await expect(added.first()).toBeVisible();
  await expect(panel).toContainText("Security policy");
  await expect(panel).toContainText("EXTERNAL");

  await anatomy(page).scrollIntoViewIfNeeded();
  const width = page.viewportSize()?.width ?? 0;
  await page.mouse.move(0, 0);
  await anatomy(page).screenshot({ path: `${SCREENSHOTS}m5-anatomy-${width}.png` });
  await expectCleanAxe(page);
  expect(offsite).toEqual([]);
});

test("switching layers off and rerunning shows what the other layers do", async ({
  page,
  request,
}) => {
  await guardNetwork(page);
  const allOn = await expectedRun(request, "inbox.hidden_forward", true);
  const toggled = await expectedRun(request, "inbox.hidden_forward", true, NO_CLEANER_NO_SCREENING);
  await page.goto("/lab/inbox?case=inbox.hidden_forward");
  const col = column(page, "With SecuLayer");

  await page.getByRole("button", { name: "Run with SecuLayer" }).click();
  await expectOutcome(col, allOn.finished);

  await setLayers(page, ["Hidden-text cleaner", "Screening"]);
  await expect(page.getByTestId("layer-menu")).toHaveText("Layers: 3 of 5 on");
  await page.getByTestId("layer-menu").click();
  const width = page.viewportSize()?.width ?? 0;
  await page.screenshot({ path: `${SCREENSHOTS}m5-layer-menu-${width}.png` });
  await expectCleanAxe(page);
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Run with SecuLayer" }).click();
  await expectOutcome(col, toggled.finished);
  await expect(col.getByTestId("outcome-banner")).toContainText(toggled.finished.banner.sentence);
  // As recorded: another layer stops it, or nothing has to.
  if (allOn.finished.outcome === "stopped" && toggled.finished.outcome === "stopped") {
    expect(toggled.finished.stopped_by).not.toBe(allOn.finished.stopped_by);
  }
});

test("a combination nobody recorded says so, and resetting the layers fixes it", async ({
  page,
  request,
}) => {
  await guardNetwork(page);
  const missing = await request.post("/api/runs", {
    data: { case_id: "inbox.polite_invoice", protected: true, layers: { hardening: false } },
  });
  // Hardening changes the prompt, so this needs recordings of its own that nobody made.
  expect(await missing.text()).toContain("wasn't recorded");
  await page.goto("/lab/inbox?case=inbox.polite_invoice");
  await setLayers(page, ["Prompt hardening"]);
  await page.getByRole("button", { name: "Run with SecuLayer" }).click();
  const col = column(page, "With SecuLayer");
  await expect(col).toContainText("This combination of layers wasn't recorded", {
    timeout: 20_000,
  });
  await col.getByRole("button", { name: "Reset the layers" }).click();
  await expect(page.getByTestId("layer-menu")).toHaveText("Layers: all 5 on");
});

test("presenter shortcuts run both sides and move between cases", async ({ page, request }) => {
  await guardNetwork(page);
  const without = await expectedRun(request, "inbox.hidden_forward", false);
  await page.goto("/lab/inbox?case=inbox.hidden_forward");
  await page.getByRole("heading", { level: 1 }).click();

  await page.keyboard.press("u");
  await expectOutcome(column(page, "Without SecuLayer"), without.finished);
  await page.keyboard.press("p");
  await expect(anatomy(page)).toBeFocused();

  await page.keyboard.press("?");
  const help = page.getByRole("dialog", { name: "Presenter shortcuts" });
  await expect(help).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(help).toBeHidden();

  await page.keyboard.press("]");
  await expect(page).not.toHaveURL(/case=inbox\.hidden_forward/);
  await page.keyboard.press("[");
  await expect(page).toHaveURL(/case=inbox\.hidden_forward/);
});
