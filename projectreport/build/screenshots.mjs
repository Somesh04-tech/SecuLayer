// Take report screenshots from the SecuLayer server in replay mode (one headless Chromium page).
// Usage: node screenshots.mjs <base-url> <out-dir>
// Run areas, the setup panel and the prompt preview are captured as whole elements, so nothing
// is cut off at the bottom of the viewport.
import { createRequire } from "node:module";
const require = createRequire(new URL("../../web/package.json", import.meta.url));
const { chromium } = require("@playwright/test");

const [base, out] = process.argv.slice(2);
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.25 });
// Only local requests: the demo never needs anything else.
await page.route("**/*", (route) =>
  new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort(),
);

async function settle() {
  await page.waitForTimeout(500);
}
async function shot(name, opts = {}) {
  await settle();
  await page.screenshot({ path: `${out}/${name}.png`, ...opts });
  console.log("saved", name);
}
async function element(name, locator) {
  await settle();
  await locator.scrollIntoViewIfNeeded();
  await locator.screenshot({ path: `${out}/${name}.png` });
  console.log("saved", name);
}
const runGrid = () =>
  page.locator("div.grid").filter({ has: page.getByRole("heading", { name: "Without SecuLayer" }) }).last();

async function runBoth() {
  await page.getByRole("button", { name: "Run without SecuLayer" }).click();
  await page.getByTestId("outcome-banner").first().waitFor({ timeout: 30000 });
  await page.getByRole("button", { name: "Run with SecuLayer" }).click();
  await page.waitForFunction(
    () => document.querySelectorAll('[data-testid="outcome-banner"]').length >= 2,
    null,
    { timeout: 30000 },
  );
  // Replay pacing is 150 ms per event on the client; give the last rows time to arrive.
  await page.waitForTimeout(4000);
}

// Home.
await page.goto(`${base}/`);
await page.getByRole("heading", { level: 1 }).waitFor();
await shot("ui-home", { fullPage: true });

// Inbox assistant, before any run.
await page.goto(`${base}/lab/inbox?case=inbox.hidden_forward`);
await page.getByRole("button", { name: "Run without SecuLayer" }).waitFor();
await shot("ui-lab-before");

// "How this app is built", expanded: the whole scenario header.
await page.getByRole("button", { name: /How this app is built/ }).click();
await element("ui-lab-how-built", page.locator("header").filter({ has: page.getByRole("heading", { level: 1 }) }));
await page.getByRole("button", { name: /How this app is built/ }).click();

// "Show what the AI reads": the whole setup panel.
await page.getByRole("switch", { name: /Show what the AI reads/ }).click();
await element("ui-lab-ai-reads", page.locator('section[aria-labelledby="setup-heading"]'));
await page.getByRole("switch", { name: /Show what the AI reads/ }).click();

// Both runs of the invisible footer, then what the model received (with SecuLayer).
await runBoth();
await element("ui-lab-inbox-runs", runGrid());
const anatomy = page.locator("section").filter({ has: page.getByRole("button", { name: "What the model received" }) });
const unclip = () =>
  page.evaluate(() => document.querySelectorAll("ol.overflow-y-auto").forEach((ol) => (ol.style.maxHeight = "none")));
await page.getByRole("button", { name: "What the model received" }).click();
await unclip();
await element("ui-lab-anatomy-with", anatomy);
// Run without SecuLayer again, so the prompt preview shows the unprotected prompt.
await page.getByRole("button", { name: "Run without SecuLayer" }).click();
await page.waitForTimeout(4000);
await unclip();
await element("ui-lab-anatomy-without", anatomy);

// Support chat: both runs of "Ignore your instructions".
await page.goto(`${base}/lab/support?case=support.override`);
await page.getByRole("button", { name: "Run without SecuLayer" }).waitFor();
await runBoth();
await element("ui-lab-support-runs", runGrid());

await browser.close();
