import { defineConfig, devices } from "@playwright/test";

/**
 * E2E config. Requires the backend stack running (docker compose up) and the
 * Next dev server (started automatically below) on :3000.
 *
 *   cd ../ && docker compose up -d postgres redis   # + backend on :8001
 *   cd frontend && pnpm exec playwright test
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
