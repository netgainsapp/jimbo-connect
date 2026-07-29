// The attendee to host loop against the LIVE deployment. A guest who has
// joined somebody else's event should be invited to host their own; a host
// should never see that pitch. Setup runs over the API, the assertion runs in
// a real browser because the whole point is that the CTA is visible.
import { test, expect, request as pwRequest } from "@playwright/test";

const STAMP = Date.now();
const PW = `E2e!${STAMP}xZ`;
const HOST = {
  email: `sdwbouldah55+e2e-growth-host-${STAMP}@gmail.com`,
  password: PW,
  name: "E2E Growth Host",
};
const GUEST = {
  email: `sdwbouldah55+e2e-growth-guest-${STAMP}@gmail.com`,
  password: PW,
  name: "E2E Growth Guest",
};

const API_URL =
  process.env.E2E_API_URL || "https://jimbo-connect-api-rdkp.onrender.com";
const WEB_URL = process.env.E2E_WEB_URL || "https://app.intro-connect.com";

let hostCtx, guestCtx, eventId, joinCode;

async function register(acct) {
  const ctx = await pwRequest.newContext({ baseURL: API_URL });
  const res = await ctx.post("/api/auth/register", { data: acct });
  expect(res.status(), await res.text()).toBe(200);
  await ctx.put("/api/profile", {
    data: { name: acct.name, role: "Organizer", company: "E2E Growth Co" },
  });
  return ctx;
}

test.beforeAll(async () => {
  hostCtx = await register(HOST);
  guestCtx = await register(GUEST);
  const ev = await hostCtx.post("/api/events", {
    data: { name: "E2E Growth Event", date: new Date().toISOString() },
  });
  expect(ev.status(), await ev.text()).toBe(200);
  const body = await ev.json();
  eventId = body.id;
  joinCode = body.join_code;
  const joined = await guestCtx.post(`/api/events/join/${joinCode}`);
  expect(joined.status(), await joined.text()).toBe(200);
});

test.afterAll(async () => {
  try {
    if (eventId) await hostCtx.delete(`/api/events/${eventId}`);
  } catch {}
  for (const ctx of [hostCtx, guestCtx]) {
    try {
      await ctx.delete("/api/profile");
    } catch {}
    await ctx.dispose();
  }
});

async function login(page, acct) {
  await page.goto(`${WEB_URL}/login`);
  await page.fill('input[type="email"]', acct.email);
  await page.fill('input[type="password"]', acct.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(events|profile)/, { timeout: 60_000 });
}

test("a guest is invited to host their own event", async ({ page }) => {
  await login(page, GUEST);

  // My Events: they have joined a room and host none, so the CTA belongs here.
  await expect(
    page.getByRole("link", { name: "Host your own event" })
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/guest-host-cta.png",
    fullPage: true,
  });

  // And again inside the directory, where guests actually spend their time.
  await page.goto(`${WEB_URL}/events/${eventId}`);
  await expect(
    page.getByRole("link", { name: "Host your own event" })
  ).toBeVisible();
});

test("the CTA deep link opens the create form", async ({ page }) => {
  await login(page, GUEST);
  await page.getByRole("link", { name: "Host your own event" }).click();
  await expect(page.getByText("Host a new event")).toBeVisible();
  // The param is consumed so a refresh does not reopen the form.
  await expect(page).toHaveURL(/\/events$/);
});

test("an existing host is never shown the pitch", async ({ page }) => {
  await login(page, HOST);
  await expect(
    page.getByRole("link", { name: "Host your own event" })
  ).toHaveCount(0);
  await page.goto(`${WEB_URL}/events/${eventId}`);
  await expect(page.getByText("Run your own events?")).toHaveCount(0);
});
