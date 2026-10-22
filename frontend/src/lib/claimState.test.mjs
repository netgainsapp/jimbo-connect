import test from "node:test";
import assert from "node:assert/strict";

import {
  claimBody,
  failureView,
  isValidEmail,
  nextStepAfterImport,
  viewFor,
} from "./claimState.js";

const EVENT = { id: "e1", name: "Denver Tech Mixer", date: "2026-11-05T01:00:00", location: "Galvanize" };
const HOST = { name: "Jane Doe" };

test("a dead link shows the no longer active page", () => {
  assert.deepEqual(viewFor({ state: "unknown" }), { view: "dead" });
  assert.deepEqual(viewFor({ state: "expired" }), { view: "dead" });
});

test("an unexpected or empty answer is treated as a dead link", () => {
  assert.deepEqual(viewFor(null), { view: "dead" });
  assert.deepEqual(viewFor({ state: "something new" }), { view: "dead" });
  assert.deepEqual(viewFor({ state: "ok" }), { view: "dead" });
});

test("a pending host is asked for an email", () => {
  assert.deepEqual(viewFor({ state: "needs_email", event: EVENT, host: HOST }), {
    view: "form",
    event: EVENT,
    host: HOST,
  });
});

test("a hosted link is ready to claim straight away", () => {
  assert.deepEqual(viewFor({ state: "ok", event: EVENT, host: HOST }), {
    view: "ready",
    event: EVENT,
    host: HOST,
  });
});

test("a 404 or 410 from the claim post is a dead link, anything else is a message", () => {
  assert.deepEqual(failureView({ status: 404 }), { view: "dead" });
  assert.deepEqual(failureView({ status: 410 }), { view: "dead" });
  const busy = failureView({ status: 429, message: "Too many attempts." });
  assert.equal(busy.view, "error");
  assert.equal(busy.message, "Too many attempts.");
  assert.equal(failureView({}).view, "error");
  assert.ok(failureView({}).message);
});

test("email validation accepts a real address and rejects the rest", () => {
  assert.equal(isValidEmail("jane@host.org"), true);
  assert.equal(isValidEmail("  Jane@Host.org "), true);
  assert.equal(isValidEmail(""), false);
  assert.equal(isValidEmail("jane"), false);
  assert.equal(isValidEmail("jane@host"), false);
  assert.equal(isValidEmail("jane @host.org"), false);
  assert.equal(isValidEmail(undefined), false);
});

test("the form post trims and lowercases the email and drops an empty name", () => {
  assert.deepEqual(claimBody({ email: "  Jane@Host.ORG ", name: "  " }), {
    email: "jane@host.org",
  });
  assert.deepEqual(claimBody({ email: "jane@host.org", name: " Jane D " }), {
    email: "jane@host.org",
    name: "Jane D",
  });
});

test("a ready claim posts an empty body", () => {
  assert.deepEqual(claimBody(null), {});
  assert.deepEqual(claimBody({}), {});
});

test("after the attendee list the photo step shows only when there is no photo", () => {
  assert.equal(nextStepAfterImport({ profile: { name: "Jane" } }), "photo");
  assert.equal(nextStepAfterImport(null), "photo");
  assert.equal(
    nextStepAfterImport({ profile: { photo_url: "data:image/png;base64,AA" } }),
    "done",
  );
});
