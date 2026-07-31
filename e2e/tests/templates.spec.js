// Host email templates against the LIVE deployment: the override round-trip
// over the API, and the /templates page in a real browser.
//
// The browser half exists because of the event page white screen of 07-31: a
// page can pass every API probe and still crash on render. Assertions here are
// PRESENCE assertions on purpose; absence checks pass on a blank page.
import { test, expect, request as pwRequest } from "@playwright/test";

const STAMP = Date.now();
const PW = `E2e!${STAMP}xZ`;
const HOST = {
  email: `sdwbouldah55+e2e-tpl-host-${STAMP}@gmail.com`,
  password: PW,
  name: "E2E Template Host",
};
const MARK = `E2E-TPL-${STAMP}`;

const API_URL =
  process.env.E2E_API_URL || "https://jimbo-connect-api-rdkp.onrender.com";
const WEB_URL = process.env.E2E_WEB_URL || "https://app.intro-connect.com";

let ctx;

test.beforeAll(async () => {
  ctx = await pwRequest.newContext({ baseURL: API_URL });
  const res = await ctx.post("/api/auth/register", { data: HOST });
  expect(res.status(), await res.text()).toBe(200);
  await ctx.put("/api/profile", {
    data: { name: HOST.name, role: "Organizer", company: "E2E Tpl Co" },
  });
});

test.afterAll(async () => {
  // Account deletion cascades to template overrides server side, so teardown
  // is one call even when a test failed mid-way.
  try {
    await ctx.delete("/api/profile");
  } catch {}
  await ctx.dispose();
});

test("the editable set is the six host templates and nothing more", async () => {
  const res = await ctx.get("/api/host/email-templates");
  expect(res.status()).toBe(200);
  const { templates } = await res.json();
  const ids = templates.map((t) => t.id);
  expect(ids).toEqual([
    "invitation",
    "save-the-date",
    "youre-in",
    "day-of",
    "post-event",
    "reconnect",
  ]);
  expect(templates.every((t) => t.customized === false)).toBe(true);
  // Every template arrives with usable default wording, not blanks.
  for (const t of templates) {
    expect(t.subject.length).toBeGreaterThan(0);
    expect(t.body.length).toBeGreaterThan(0);
    expect(t.title.length).toBeGreaterThan(0);
  }
});

test("password reset cannot be read or written through this surface", async () => {
  const put = await ctx.put("/api/host/email-templates/password-reset", {
    data: { subject: "EVIL", body: "EVIL" },
  });
  expect(put.status()).toBe(404);
  const del = await ctx.delete("/api/host/email-templates/password-reset");
  expect(del.status()).toBe(404);
});

test("an override round-trips, and reset restores the default", async () => {
  const original = await (await ctx.get("/api/host/email-templates")).json();
  const defaultSubject = original.templates.find(
    (t) => t.id === "invitation"
  ).subject;

  const put = await ctx.put("/api/host/email-templates/invitation", {
    data: {
      subject: `${MARK} come to {event_name}`,
      body: `Hi {attendee_name}, ${MARK}. {site_url}`,
    },
  });
  expect(put.status(), await put.text()).toBe(200);
  const saved = await put.json();
  expect(saved.customized).toBe(true);
  expect(saved.subject).toContain(MARK);

  const listed = await (await ctx.get("/api/host/email-templates")).json();
  const mine = listed.templates.find((t) => t.id === "invitation");
  expect(mine.customized).toBe(true);
  expect(mine.subject).toContain(MARK);
  // The identity fields stay the platform's: the host edits words, not labels.
  expect(mine.title.length).toBeGreaterThan(0);

  const reset = await ctx.delete("/api/host/email-templates/invitation");
  expect(reset.status()).toBe(200);
  const after = await (await ctx.get("/api/host/email-templates")).json();
  const restored = after.templates.find((t) => t.id === "invitation");
  expect(restored.customized).toBe(false);
  expect(restored.subject).toBe(defaultSubject);
});

test("blank overrides are refused", async () => {
  const res = await ctx.put("/api/host/email-templates/invitation", {
    data: { subject: "   ", body: "b" },
  });
  // Pydantic min_length rejects the empty case; the module catches
  // whitespace-only. Either way nothing blank is stored.
  expect([400, 404, 422]).toContain(res.status());
  const listed = await (await ctx.get("/api/host/email-templates")).json();
  expect(
    listed.templates.find((t) => t.id === "invitation").customized
  ).toBe(false);
});

test("the templates page renders, saves an edit, and shows Customized", async ({
  page,
}) => {
  await page.goto(`${WEB_URL}/login`);
  await page.fill('input[type="email"]', HOST.email);
  await page.fill('input[type="password"]', HOST.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(events|profile)/, { timeout: 60_000 });

  await page.goto(`${WEB_URL}/templates`);

  // Presence first: the page actually rendered.
  await expect(
    page.getByRole("heading", { name: "Email templates" })
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Invitation \(with login\)/ })
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /save the date/i })
  ).toBeVisible();

  // Edit the invitation in the UI and save.
  await page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: /Invitation \(with login\)/ }) })
    .getByRole("button", { name: "Edit" })
    .click();
  const subject = page.locator("#tpl-subject-invitation");
  await expect(subject).toBeVisible();
  await subject.fill(`${MARK}-UI You're invited to {event_name}`);
  await page.getByRole("button", { name: "Save template" }).click();

  await expect(page.getByText("Customized")).toBeVisible();

  // And the server agrees it stuck.
  const listed = await (await ctx.get("/api/host/email-templates")).json();
  expect(
    listed.templates.find((t) => t.id === "invitation").subject
  ).toContain(`${MARK}-UI`);

  // Leave the account clean for the API reset test ordering independence.
  await ctx.delete("/api/host/email-templates/invitation");
});
