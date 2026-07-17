// Billing surface + upgrade page against the LIVE deployment. API half proves
// the plan/checkout endpoints the SPA calls; the browser half proves the
// /upgrade page renders plans and offers checkout to a free-plan user.
//
// Same side-effect discipline as flow.spec.js: plus-addressed account on the
// owner's inbox, everything deleted in afterAll. Checkout sessions are created
// but never paid, so no subscription or charge results.
import { test, expect, request as pwRequest } from "@playwright/test";

const STAMP = Date.now();
const ACCT = {
  email: `sdwbouldah55+e2e-billing-${STAMP}@gmail.com`,
  password: `E2e!${STAMP}xZ`,
  name: "E2E Billing",
};

const API_URL =
  process.env.E2E_API_URL || "https://jimbo-connect-api-rdkp.onrender.com";
const WEB_URL = process.env.E2E_WEB_URL || "https://app.intro-connect.com";

let ctx;

test.beforeAll(async () => {
  ctx = await pwRequest.newContext({ baseURL: API_URL });
  const res = await ctx.post("/api/auth/register", { data: ACCT });
  expect(res.status(), await res.text()).toBe(200);
});

test.afterAll(async () => {
  try {
    await ctx.delete("/api/profile");
  } catch {}
  await ctx.dispose();
});

test("billing status: new account is free, billing configured, limit 1", async () => {
  const res = await ctx.get("/api/billing/status");
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.plan).toBe("free");
  expect(body.configured).toBe(true);
  expect(body.event_limit).toBe(1);
});

test("checkout returns a Stripe URL for both paid plans", async () => {
  for (const plan of ["starter", "pro"]) {
    const res = await ctx.post("/api/billing/checkout", { data: { plan } });
    expect(res.status(), await res.text()).toBe(200);
    const { url } = await res.json();
    expect(url).toContain("checkout.stripe.com");
  }
});

test("checkout rejects an unknown plan", async () => {
  const res = await ctx.post("/api/billing/checkout", {
    data: { plan: "enterprise" },
  });
  expect(res.status()).toBe(400);
});

test("upgrade page renders plans and offers checkout to a free user", async ({
  page,
}) => {
  // Unauthenticated /upgrade bounces to login (RequireAuth).
  await page.goto(`${WEB_URL}/upgrade`);
  await expect(page).toHaveURL(/\/login/);

  // Log in as the test account through the real form.
  await page.fill('input[type="email"]', ACCT.email);
  await page.fill('input[type="password"]', ACCT.password);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/(events|profile)/);

  await page.goto(`${WEB_URL}/upgrade`);
  await expect(
    page.getByRole("heading", { name: "Plans" })
  ).toBeVisible();
  await expect(page.getByText("$39")).toBeVisible();
  await expect(page.getByText("$99")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Upgrade to Pro" })
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Current plan" })
  ).toBeDisabled();

  await page.screenshot({
    path: "test-results/upgrade-page.png",
    fullPage: true,
  });
});
