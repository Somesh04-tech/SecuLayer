import AxeBuilder from "@axe-core/playwright";
import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

/**
 * The featured cases, run both ways in replay mode (docs/PLAN.md §9 M4). Expected outcomes
 * come from the API's own replay of the recording, never hard-coded, so the spec holds for
 * the FakeModel fixtures (tests/e2e_fixtures.py) and for real recordings alike.
 */

const SCREENSHOTS = fileURLToPath(new URL("../../artifacts/screenshots/", import.meta.url));

interface Finished {
  outcome: string;
  banner: { title: string; sentence: string };
  stopped_by: string | null;
}

async function expectedRun(
  request: APIRequestContext,
  caseId: string,
  isProtected: boolean,
): Promise<{ finished: Finished; attacker: { destination: string }[] }> {
  const response = await request.post("/api/runs", {
    data: { case_id: caseId, protected: isProtected },
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

async function expectCleanAxe(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(" ")).join(", ")})`);
  expect(serious).toEqual([]);
}

function column(page: Page, name: "Without SecuLayer" | "With SecuLayer"): Locator {
  return page.getByRole("region", { name, exact: true });
}

async function expectOutcome(col: Locator, finished: Finished) {
  const banner = col.getByTestId("outcome-banner");
  await expect(banner).toBeVisible({ timeout: 20_000 });
  await expect(banner).toHaveAttribute("data-outcome", finished.outcome);
  await expect(banner).toContainText(finished.banner.title);
}

async function runBothWays(page: Page, request: APIRequestContext, caseId: string) {
  const without = await expectedRun(request, caseId, false);
  const withLayer = await expectedRun(request, caseId, true);

  await page.getByRole("button", { name: "Run without SecuLayer" }).click();
  await expectOutcome(column(page, "Without SecuLayer"), without.finished);
  for (const hit of without.attacker) {
    await expect(column(page, "Without SecuLayer").getByTestId("attacker-server")).toContainText(
      hit.destination.split("@").pop() ?? hit.destination,
    );
  }

  await page.getByRole("button", { name: "Run with SecuLayer" }).click();
  await expectOutcome(column(page, "With SecuLayer"), withLayer.finished);
  return { without, withLayer };
}

test("inbox assistant: hijacked without SecuLayer, stopped with it", async ({
  page,
  request,
}) => {
  const offsite = await guardNetwork(page);
  await page.goto("/");
  await page.getByRole("link", { name: "Start with the inbox assistant" }).click();
  await expect(page).toHaveURL(/\/lab\/inbox/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Inbox assistant");
  const width = page.viewportSize()?.width ?? 0;
  await page.screenshot({ path: `${SCREENSHOTS}m4-lab-before-${width}.png`, fullPage: true });
  await expectCleanAxe(page);

  const { without, withLayer } = await runBothWays(page, request, "inbox.hidden_forward");
  // The featured attack: the fixtures (and the plan) expect the hijack to reach the attacker.
  if (without.finished.outcome === "hijacked") {
    await expect(column(page, "Without SecuLayer").getByTestId("attacker-server")).toContainText(
      "mail-backup.example",
    );
  }
  if (withLayer.finished.outcome === "stopped") {
    const layerNames = /hidden-text cleaner|screening|prompt hardening|tool guard|output guard/i;
    await expect(column(page, "With SecuLayer").getByTestId("outcome-banner")).toContainText(
      layerNames,
    );
  }
  await page.mouse.move(0, 0);
  await page.screenshot({ path: `${SCREENSHOTS}m4-lab-after-${width}.png`, fullPage: true });
  await expectCleanAxe(page);
  expect(offsite).toEqual([]);
});

test("support chat: the override attack, both ways", async ({ page, request }) => {
  const offsite = await guardNetwork(page);
  await page.goto("/");
  await page.getByRole("link", { name: /Support chat/ }).first().click();
  await expect(page).toHaveURL(/\/lab\/support/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Support chat");
  await runBothWays(page, request, "support.override");
  await expectCleanAxe(page);
  expect(offsite).toEqual([]);
});

test("trial navigator replays another recorded run", async ({ page, request }) => {
  await guardNetwork(page);
  const second = await request.post("/api/runs", {
    data: { case_id: "inbox.hidden_forward", protected: false, trial: 2 },
  });
  const started = JSON.parse((await second.text()).split("\n")[0] ?? "{}") as {
    trials_available: number;
  };
  test.skip(started.trials_available < 2, "only one recorded run of this case");
  await page.goto("/lab/inbox?case=inbox.hidden_forward");
  await page.getByRole("button", { name: "Run without SecuLayer" }).click();
  const col = column(page, "Without SecuLayer");
  await expect(col.getByTestId("outcome-banner")).toBeVisible({ timeout: 20_000 });
  await expect(col).toContainText(`Recorded run 1 of ${started.trials_available}`);
  await col.getByRole("button", { name: /next recorded run/i }).click();
  await expect(col).toContainText(`Recorded run 2 of ${started.trials_available}`, {
    timeout: 20_000,
  });
});

/** Presses Tab until `target` has focus (keyboard-only navigation). */
async function tabTo(page: Page, target: Locator, max = 80) {
  for (let i = 0; i < max; i += 1) {
    if (await target.evaluate((el) => el === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
  throw new Error(`Couldn't reach ${target.toString()} with Tab`);
}

test("keyboard only: the featured flow with Tab, arrows, Enter and Space", async ({
  page,
  request,
}) => {
  await guardNetwork(page);
  const without = await expectedRun(request, "inbox.hidden_forward", false);
  const withLayer = await expectedRun(request, "inbox.hidden_forward", true);
  const support = await expectedRun(request, "support.override", false);

  await page.goto("/");
  await tabTo(page, page.getByRole("link", { name: "Start with the inbox assistant" }));
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Inbox assistant");

  await tabTo(page, page.getByRole("button", { name: "Run without SecuLayer" }));
  await page.keyboard.press("Enter");
  await expectOutcome(column(page, "Without SecuLayer"), without.finished);

  await tabTo(page, page.getByRole("button", { name: "Run with SecuLayer" }));
  await page.keyboard.press("Space");
  await expectOutcome(column(page, "With SecuLayer"), withLayer.finished);

  // Arrow keys move through the case list; Enter selects.
  await page.goto("/lab/support");
  const options = page.getByRole("option");
  await tabTo(page, options.first());
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowUp");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/case=support\.override/);
  await tabTo(page, page.getByRole("button", { name: "Run without SecuLayer" }));
  await page.keyboard.press("Space");
  await expectOutcome(column(page, "Without SecuLayer"), support.finished);
});
