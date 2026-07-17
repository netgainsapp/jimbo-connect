// Full post-event networking flow against the LIVE API, exercised through the
// same HTTP surface the SPA uses. Each user gets an isolated request context
// (its own cookie jar), so this proves cookie-based auth + the cross-user
// authorization gate end to end.
//
// Side-effect discipline: test accounts use Gmail plus-addressing on the
// owner's own inbox (clean delivery, no bounces, no suppression pollution) and
// EVERYTHING created here is deleted in afterAll, plus a leftover sweep.
import { test, expect, request as pwRequest } from "@playwright/test";

const STAMP = Date.now();
const PW = `E2e!${STAMP}xZ`;
const TEST_TLD = "@gmail.com";
const inbox = (tag) => `sdwbouldah55+e2e-${tag}-${STAMP}${TEST_TLD}`;

const HOST = { email: inbox("host"), password: PW, name: "E2E Host" };
const GUEST = { email: inbox("guest"), password: PW, name: "E2E Guest" };

let hostCtx, guestCtx;
let hostId, guestId, eventId, joinCode;

async function newCtx() {
  return pwRequest.newContext({
    baseURL: process.env.E2E_API_URL || "https://jimbo-connect-api-rdkp.onrender.com",
  });
}

test.beforeAll(async () => {
  hostCtx = await newCtx();
  guestCtx = await newCtx();
});

test.afterAll(async () => {
  // Best-effort teardown: delete the event, then both accounts. Never throw
  // from cleanup so a mid-test failure still tidies up.
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

test("register sets an httpOnly session and returns the user", async () => {
  const res = await hostCtx.post("/api/auth/register", { data: HOST });
  expect(res.status(), await res.text()).toBe(200);
  const body = await res.json();
  expect(body.user.email).toBe(HOST.email.toLowerCase());
  hostId = body.user.id;

  // The session must ride the cookie, not the response token.
  const me = await hostCtx.get("/api/auth/me");
  expect(me.status()).toBe(200);
});

test("second user registers and both sessions are independent", async () => {
  const res = await guestCtx.post("/api/auth/register", { data: GUEST });
  expect(res.status(), await res.text()).toBe(200);
  guestId = (await res.json()).user.id;
  expect(guestId).not.toBe(hostId);
});

test("cross-user read is blocked before they share an event (authz gate)", async () => {
  // The IDOR/BOLA fix: strangers get an opaque 404, not another user's PII.
  const res = await hostCtx.get(`/api/profile/${guestId}`);
  expect(res.status()).toBe(404);
});

test("host creates an event and gets a join code", async () => {
  const res = await hostCtx.post("/api/events", {
    data: { name: `E2E Event ${STAMP}`, date: "2099-01-01T18:00:00Z", location: "E2E" },
  });
  expect(res.status(), await res.text()).toBe(200);
  const ev = await res.json();
  eventId = ev.id;
  joinCode = ev.join_code;
  expect(joinCode).toBeTruthy();
});

test("guest joins with the code and appears in the attendee directory", async () => {
  const join = await guestCtx.post(`/api/events/join/${joinCode}`);
  expect(join.status(), await join.text()).toBe(200);

  const att = await hostCtx.get(`/api/events/${eventId}/attendees`);
  expect(att.status()).toBe(200);
  const ids = (await att.json()).map((a) => a.id);
  expect(ids).toContain(guestId);
});

test("sharing an event now unlocks cross-user profile view", async () => {
  const res = await hostCtx.get(`/api/profile/${guestId}`);
  expect(res.status(), await res.text()).toBe(200);
});

test("host saves the guest as a contact with a private note", async () => {
  const res = await hostCtx.post("/api/contacts/save", {
    data: { contact_id: guestId, note: "met at the e2e event" },
  });
  expect(res.status(), await res.text()).toBe(200);
  const list = await hostCtx.get("/api/contacts");
  expect(list.status()).toBe(200);
  // SavedContactPublic: the saved person is contact_id (id is the record id).
  const saved = (await list.json()).map((c) => c.contact_id);
  expect(saved).toContain(guestId);
});

test("host can message the guest and the guest receives the thread", async () => {
  const send = await hostCtx.post("/api/messages", {
    data: { to_user_id: guestId, text: "hello from the e2e host" },
  });
  expect(send.status(), await send.text()).toBe(200);

  const threads = await guestCtx.get("/api/messages/threads");
  expect(threads.status()).toBe(200);
  expect(await threads.text()).toContain("hello from the e2e host");
});

test("logout clears the session", async () => {
  const out = await hostCtx.post("/api/auth/logout");
  expect(out.status()).toBe(200);
  const me = await hostCtx.get("/api/auth/me");
  expect(me.status()).toBe(401);
  // log back in so afterAll can still delete this account
  const back = await hostCtx.post("/api/auth/login", {
    data: { email: HOST.email, password: HOST.password },
  });
  expect(back.status()).toBe(200);
});
