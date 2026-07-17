// E2E config for Intro Connect. Targets a LIVE deployment (no local DB exists).
// Render free tier cold-starts (~40s), so timeouts are generous and retries on.
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  // A cold start can take ~40s; each whole test gets room for several such hits.
  timeout: 180_000,
  expect: { timeout: 60_000 },
  fullyParallel: false, // shared prod DB: keep flows sequential and predictable
  workers: 1,
  retries: 1, // ride out a single cold-start hiccup, not real failures
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_API_URL || "https://jimbo-connect-api-rdkp.onrender.com",
    actionTimeout: 60_000,
    ignoreHTTPSErrors: false,
  },
});
