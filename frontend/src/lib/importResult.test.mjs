import test from "node:test";
import assert from "node:assert/strict";

import { importOutcome } from "./importResult.js";

test("a clean roster import says what was added and what was emailed", () => {
  const out = importOutcome({
    created: 12,
    added_to_event: 12,
    emailed: 12,
    email_failures: {},
  });
  assert.equal(out.type, "success");
  assert.match(out.message, /12 guests added/);
  assert.match(out.message, /12 emailed/);
});

test("emails that failed are surfaced, and the accounts are still acknowledged", () => {
  const out = importOutcome({
    created: 40,
    added_to_event: 40,
    emailed: 0,
    email_failures: { "domain not verified": 40 },
  });
  assert.equal(out.type, "error");
  assert.match(out.message, /40 guests added/);
  assert.match(out.message, /domain not verified/);
});

test("no emails and no failures is stated plainly rather than implied as sent", () => {
  // Email off, or every address already had an account. Either way, claiming
  // "40 guests invited" here is the bug this replaces.
  const out = importOutcome({
    created: 0,
    added_to_event: 40,
    emailed: 0,
    email_failures: {},
  });
  assert.equal(out.type, "success");
  assert.doesNotMatch(out.message, /invited/i);
  assert.match(out.message, /no invitation/i);
});

test("guests who already had accounts do not read as a problem", () => {
  const out = importOutcome({
    created: 3,
    added_to_event: 10,
    emailed: 3,
    email_failures: {},
  });
  assert.equal(out.type, "success");
  assert.match(out.message, /10 guests added/);
  assert.match(out.message, /3 emailed/);
});

test("one guest is not pluralised", () => {
  const out = importOutcome({ created: 1, added_to_event: 1, emailed: 1, email_failures: {} });
  assert.match(out.message, /1 guest added/);
});

test("a partial email failure reports both numbers", () => {
  const out = importOutcome({
    created: 10,
    added_to_event: 10,
    emailed: 6,
    email_failures: { suppressed: 4 },
  });
  assert.equal(out.type, "error");
  assert.match(out.message, /6 emailed/);
  assert.match(out.message, /4/);
  assert.match(out.message, /suppressed/);
});

test("a response without the email fields still describes the import", () => {
  const out = importOutcome({ created: 5, added_to_event: 5 });
  assert.equal(out.type, "success");
  assert.match(out.message, /5 guests added/);
});
