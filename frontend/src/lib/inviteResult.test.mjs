import test from "node:test";
import assert from "node:assert/strict";

import { inviteOutcome } from "./inviteResult.js";

test("a clean send reads as success", () => {
  const out = inviteOutcome({ invited: 3, sent: 3, failed: 0, skipped_recent: 0, failures: {} });
  assert.equal(out.type, "success");
  assert.match(out.message, /Invited 3 guests/);
});

test("one guest is not pluralised", () => {
  const out = inviteOutcome({ invited: 1, sent: 1, failed: 0, skipped_recent: 0, failures: {} });
  assert.match(out.message, /Invited 1 guest\b/);
});

test("a send where nothing left is an error, not a success", () => {
  // The whole point: this used to render as "Invited 40 guests".
  const out = inviteOutcome({
    invited: 40,
    sent: 0,
    failed: 40,
    skipped_recent: 0,
    failures: { "domain not verified": 40 },
  });
  assert.equal(out.type, "error");
  assert.doesNotMatch(out.message, /^Invited 40/);
  assert.match(out.message, /domain not verified/);
});

test("a partial send reports both halves", () => {
  const out = inviteOutcome({
    invited: 10,
    sent: 7,
    failed: 3,
    skipped_recent: 0,
    failures: { suppressed: 3 },
  });
  assert.equal(out.type, "error");
  assert.match(out.message, /7 of 10/);
  assert.match(out.message, /suppressed/);
});

test("the dominant reason is the one shown", () => {
  const out = inviteOutcome({
    invited: 9,
    sent: 0,
    failed: 9,
    failures: { "rate limited": 2, "domain not verified": 7 },
  });
  assert.match(out.message, /domain not verified/);
  assert.doesNotMatch(out.message, /rate limited/);
});

test("an unhelpful reason is left out rather than shown raw", () => {
  const out = inviteOutcome({ invited: 2, sent: 0, failed: 2, failures: { unknown: 2 } });
  assert.equal(out.type, "error");
  assert.doesNotMatch(out.message, /unknown/);
});

test("a long reason is truncated so the toast stays readable", () => {
  const long = "x".repeat(300);
  const out = inviteOutcome({ invited: 1, sent: 0, failed: 1, failures: { [long]: 1 } });
  assert.ok(out.message.length < 160, `too long: ${out.message.length}`);
});

test("unconfigured email says so instead of claiming a send", () => {
  const out = inviteOutcome({ invited: 0, sent: 0, skipped: "email_not_configured" });
  assert.equal(out.type, "error");
  assert.match(out.message, /not set up/i);
});

test("everyone already invited is explained, not reported as zero", () => {
  const out = inviteOutcome({ invited: 0, sent: 0, failed: 0, skipped_recent: 5, failures: {} });
  assert.equal(out.type, "success");
  assert.match(out.message, /already invited/i);
});

test("a successful send still mentions who was skipped as recent", () => {
  const out = inviteOutcome({ invited: 2, sent: 2, failed: 0, skipped_recent: 3, failures: {} });
  assert.equal(out.type, "success");
  assert.match(out.message, /Invited 2 guests/);
  assert.match(out.message, /3 guests/);
});

test("a response missing the new fields still degrades to something true", () => {
  // Guards the deploy window where the client is ahead of the API.
  const out = inviteOutcome({ invited: 4, sent: 4 });
  assert.equal(out.type, "success");
  assert.match(out.message, /Invited 4 guests/);
});
