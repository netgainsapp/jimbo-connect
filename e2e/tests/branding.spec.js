// Host branding (Pro) against the LIVE deployment: the plan gate holds for
// free accounts, the public logo endpoint 404s for unbranded hosts, and the
// profile page shows the locked "Your brand" card with the plans link.
//
// Same discipline as the other specs: plus-addressed account, deleted in
// afterAll. The pro happy path is covered by backend unit tests (plan logic,
// image pipeline, email render); exercising it here would require a paid
// account, which CI must never create.
import { test, expect, request as pwRequest } from "@playwright/test";

const STAMP = Date.now();
const ACCT = {
  email: `sdwbouldah55+e2e-branding-${STAMP}@gmail.com`,
  password: `E2e!${STAMP}xZ`,
  name: "E2E Branding",
};

const API_URL =
  process.env.E2E_API_URL || "https://jimbo-connect-api-rdkp.onrender.com";
const WEB_URL = process.env.E2E_WEB_URL || "https://app.intro-connect.com";

let ctx;

test.beforeAll(async () => {
  ctx = await pwRequest.newContext({ baseURL: API_URL });
  const res = await ctx.post("/api/auth/register", { data: ACCT });
  expect(res.status(), await res.text()).toBe(200);
  // Complete the profile so /profile (edit mode, where the brand card lives)
  // is reachable in the browser test.
  await ctx.put("/api/profile", {
    data: { name: ACCT.name, role: "Host", company: "E2E Test Co" },
  });
});

test.afterAll(async () => {
  try {
    await ctx.delete("/api/profile");
  } catch {}
  await ctx.dispose();
});

test("free account: branding reads as locked out but visible", async () => {
  const res = await ctx.get("/api/branding");
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.allowed).toBe(false);
  expect(body.active).toBe(false);
  expect(body.plan).toBe("free");
});

test("free account: setting an accent is rejected with the upgrade message", async () => {
  const res = await ctx.put("/api/branding", { data: { accent: "#0a5c36" } });
  expect(res.status()).toBe(403);
  expect((await res.json()).detail).toContain("Pro");
});

test("free account: logo upload is rejected by the plan gate", async () => {
  const res = await ctx.post("/api/branding/logo", {
    multipart: {
      file: {
        name: "logo.png",
        mimeType: "image/png",
        buffer: Buffer.from([0x89, 0x50, 0x4e, 0x47]),
      },
    },
  });
  expect(res.status()).toBe(403);
});

test("public logo endpoint 404s for unknown and unbranded hosts", async () => {
  const bogus = await ctx.get("/api/branding/000000000000000000000000/logo.png");
  expect(bogus.status()).toBe(404);
  const invalid = await ctx.get("/api/branding/not-an-id/logo.png");
  expect(invalid.status()).toBe(404);
});

test("profile page shows the locked brand card with a plans link", async ({
  page,
}) => {
  await page.goto(`${WEB_URL}/login`);
  await page.fill('input[type="email"]', ACCT.email);
  await page.fill('input[type="password"]', ACCT.password);
  await page.click('button[type="submit"]');
  // Fresh account: complete the minimal profile so /profile is reachable.
  await expect(page).toHaveURL(/\/(profile\/setup|events)/);

  await page.goto(`${WEB_URL}/profile`);
  await expect(page.getByText("Your brand")).toBeVisible();
  await expect(page.getByText("See plans")).toBeVisible();
  await page.screenshot({
    path: "test-results/brand-card-locked.png",
    fullPage: true,
  });
});
