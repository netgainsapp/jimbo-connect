// The full paid happy path, on demand: register, buy Pro through the REAL
// Stripe checkout (test mode, documented 4242 sandbox card), then exercise
// host branding end to end: accent, logo upload, public logo serving, and the
// branded event directory in a real browser.
//
// OPT-IN: runs only with E2E_PRO_FLOW=1. It is deliberately not part of the
// routine suite because every run creates a test-mode Stripe subscription
// (harmless sandbox clutter, wipe via Stripe's "delete all test data"), and
// because it must never run once Stripe flips to LIVE mode, where the sandbox
// card declines. The account itself is plus-addressed and self-deleting.
import { test, expect, request as pwRequest } from "@playwright/test";

const RUN = process.env.E2E_PRO_FLOW === "1";
const STAMP = Date.now();
const ACCT = {
  email: `sdwbouldah55+e2e-pro-${STAMP}@gmail.com`,
  password: `E2e!${STAMP}xZ`,
  name: "E2E Pro Host",
};

const API_URL =
  process.env.E2E_API_URL || "https://jimbo-connect-api-rdkp.onrender.com";
const WEB_URL = process.env.E2E_WEB_URL || "https://app.intro-connect.com";

// 1x1 red pixel PNG, valid input for the Pillow pipeline.
const TINY_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64"
);

let ctx;
let eventId;

test.describe("pro happy path (opt-in)", () => {
  test.skip(!RUN, "Set E2E_PRO_FLOW=1 to run the paid-flow suite (test mode only)");
  // No retries: a retry spawns a fresh worker whose beforeAll registers a new
  // free account, poisoning the later tests that depend on the paid state.
  test.describe.configure({ retries: 0 });

  test.beforeAll(async () => {
    ctx = await pwRequest.newContext({ baseURL: API_URL });
    const res = await ctx.post("/api/auth/register", { data: ACCT });
    expect(res.status(), await res.text()).toBe(200);
    await ctx.put("/api/profile", {
      data: { name: ACCT.name, role: "Host", company: "E2E Pro Co" },
    });
  });

  test.afterAll(async () => {
    try {
      if (eventId) await ctx.delete(`/api/events/${eventId}`);
    } catch {}
    try {
      await ctx.delete("/api/branding");
    } catch {}
    try {
      await ctx.delete("/api/profile");
    } catch {}
    await ctx.dispose();
  });

  test("buy Pro through Stripe test checkout and the webhook flips the plan", async ({
    page,
  }) => {
    test.setTimeout(300_000);
    // Checkout session via the API (what the upgrade page calls), then drive
    // Stripe's hosted page like a human would.
    const co = await ctx.post("/api/billing/checkout", { data: { plan: "pro" } });
    expect(co.status(), await co.text()).toBe(200);
    const { url } = await co.json();
    expect(url).toContain("checkout.stripe.com");

    await page.goto(url);
    // customer_email is preset on the session, so Stripe shows no email input.
    // If the payment methods render as an accordion (Link first), open card.
    const cardNumber = page.locator('input[name="cardNumber"]');
    try {
      await cardNumber.waitFor({ timeout: 30_000 });
    } catch {
      const cardTab = page
        .locator('[data-testid="card-accordion-item"], button:has-text("Card")')
        .first();
      await cardTab.click();
      await cardNumber.waitFor({ timeout: 30_000 });
    }
    await cardNumber.fill("4242 4242 4242 4242");
    await page.fill('input[name="cardExpiry"]', "12 / 34");
    await page.fill('input[name="cardCvc"]', "123");
    await page.fill('input[name="billingName"]', ACCT.name);
    const zip = page.locator('input[name="billingPostalCode"]');
    if (await zip.count()) await zip.fill("80302");
    // Stripe pre-checks "Save my information" (Link), which then demands a
    // phone number and blocks submit. Opt out.
    const savePass = page.getByRole("checkbox", { name: /save my information/i });
    if ((await savePass.count()) && (await savePass.first().isChecked())) {
      await savePass.first().uncheck();
    }
    await page.click('[data-testid="hosted-payment-submit-button"]');

    // Back to the app with the success flag.
    try {
      await page.waitForURL(/upgraded=1/, { timeout: 120_000 });
    } catch (e) {
      await page.screenshot({
        path: "test-results/checkout-debug.png",
        fullPage: true,
      });
      throw e;
    }

    // The webhook applies the plan asynchronously; poll until it lands.
    await expect
      .poll(
        async () => (await (await ctx.get("/api/billing/status")).json()).plan,
        { timeout: 90_000, intervals: [3000] }
      )
      .toBe("pro");
  });

  test("pro host sets accent and logo; guardrails and serving work", async () => {
    const acc = await ctx.put("/api/branding", { data: { accent: "#1db954" } });
    expect(acc.status(), await acc.text()).toBe(200);
    const accBody = await acc.json();
    expect(accBody.accent).toBe("#1db954");
    // Light accent must have been auto darkened for text use.
    expect(accBody.accent_dark).not.toBe("#1db954");

    const up = await ctx.post("/api/branding/logo", {
      multipart: {
        file: { name: "logo.png", mimeType: "image/png", buffer: TINY_PNG },
      },
    });
    expect(up.status(), await up.text()).toBe(200);
    const upBody = await up.json();
    expect(upBody.active).toBe(true);
    expect(upBody.logo_url).toContain("/logo.png");

    // Public serving: anonymous fetch returns a real PNG.
    const anon = await pwRequest.newContext();
    const img = await anon.get(upBody.logo_url);
    expect(img.status()).toBe(200);
    expect(img.headers()["content-type"]).toBe("image/png");
    await anon.dispose();
  });

  test("the host's event directory renders the brand", async ({ page }) => {
    const ev = await ctx.post("/api/events", {
      data: { name: "E2E Branded Event", date: new Date().toISOString() },
    });
    expect(ev.status(), await ev.text()).toBe(200);
    const evBody = await ev.json();
    eventId = evBody.id;

    const got = await ctx.get(`/api/events/${eventId}`);
    const gotBody = await got.json();
    expect(gotBody.host_branding).toBeTruthy();
    expect(gotBody.host_branding.accent_dark).toMatch(/^#[0-9a-f]{6}$/);

    await page.goto(`${WEB_URL}/login`);
    await page.fill('input[type="email"]', ACCT.email);
    await page.fill('input[type="password"]', ACCT.password);
    await page.click('button[type="submit"]');
    // Wait for the session to land before deep-linking, or RequireAuth
    // bounces the not-yet-authenticated visitor back to /login.
    await page.waitForURL(/\/(events|profile)/, { timeout: 60_000 });
    await page.goto(`${WEB_URL}/events/${eventId}`);
    await expect(page.getByAltText("Event host logo")).toBeVisible();
    await expect(page.getByText("via Intro Connect")).toBeVisible();
    await page.screenshot({
      path: "test-results/branded-directory.png",
      fullPage: true,
    });
  });
});
