import { defineConfig, devices } from "@playwright/test";

const PORT = 8766;

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../artifacts/test-results",
  reporter: [["list"], ["html", { outputFolder: "../artifacts/playwright-report", open: "never" }]],
  // The laptop has 2 cores: one worker, no parallelism, no retries hiding flakes.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  forbidOnly: true,
  timeout: 60_000,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    headless: true,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "desktop-1440",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "desktop-1280",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 720 } },
    },
  ],
  webServer: {
    command: `uv run seculayer serve --port ${PORT} --mode replay`,
    cwd: "..",
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "ignore",
    stderr: "pipe",
  },
});
