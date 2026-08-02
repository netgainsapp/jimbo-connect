// The upgrade CTA must be reachable from the nav on a free plan.
//
// Regression test for a real conversion defect found 2026-08-01: /upgrade
// existed but NOTHING in the app's navigation pointed at it. Every route in was
// either buried inside the create-event form or triggered by failure (hit the
// event limit, get a 403, get redirected). A free user who simply wanted to pay
// had nowhere to click. If the nav link is ever dropped again, this fails.
//
// Same side-effect discipline as billing.spec.js: the account is registered by
// this test on a plus-addressed inbox and deleted in afterAll. No checkout is
// started, so no charge or subscription can result.
import { test, expect, request as pwRequest } from "@playwright/test";

const STAMP = Date.now();
const ACCT = {
  email: `sdwbouldah55+e2e-upgradecta-${STAMP}@gmail.com`,
  password: `E2e!${STAMP}xZ`,
  name: "E2E Upgrade CTA",
};

const API_URL =
  process.env.E2E_API_URL || "https://jimbo-connect-api-rdkp.onrender.com";
const WEB_URL = process.env.E2E_WEB_URL || "https://app.intro-connect.com";

let ctx;

test.beforeAll(async () => {
  ctx = await pwRequest.newContext({ baseURL: API_URL });
  const res = await ctx.post("/api/auth/register", { data: ACCT });
  expect(res.status(), await res.text()).toBe(200);
  // A fresh signup has an incomplete profile, and RequireAuth pins those to
  // /profile/setup. Fill it over the API so the browser half exercises the
  // ordinary logged-in nav rather than the onboarding detour.
  const prof = await ctx.put("/api/profile", {
    data: { name: ACCT.name, role: "Organizer", company: "E2E Co" },
  });
  expect(prof.status(), await prof.text()).toBe(200);
});

test.afterAll(async () => {
  // Leave nothing behind.
  await ctx.post("/api/auth/login", { data: ACCT }).catch(() => {});
  await ctx.delete("/api/profile").catch(() => {});
  await ctx.dispose();
});

test("a free user can reach the upgrade page from the nav", async ({ page }) => {
  await page.goto(`${WEB_URL}/login`);
  await page.fill('input[type="email"]', ACCT.email);
  await page.fill('input[type="password"]', ACCT.password);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/events/);

  // The whole point: visible without opening a form or hitting a limit.
  const upgrade = page.getByRole("link", { name: /upgrade/i }).first();
  await expect(upgrade).toBeVisible();

  await page.screenshot({
    path: "test-results/upgrade-cta-nav.png",
    fullPage: false,
  });

  await upgrade.click();
  await expect(page).toHaveURL(/\/upgrade/);
  await expect(page.getByRole("heading", { name: "Plans" })).toBeVisible();
});
