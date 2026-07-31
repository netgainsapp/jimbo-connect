import test from "node:test";
import assert from "node:assert/strict";
import {
  MAILTO_SAFE_LENGTH,
  buildAnnouncementMailto,
} from "./announcementMail.js";

const many = (n) =>
  Array.from({ length: n }, (_, i) => `attendee${i}.longish.name@example-company.com`);

test("puts every recipient in bcc, never to or cc", () => {
  const { href, recipientCount } = buildAnnouncementMailto({
    subject: "Doors open at 6",
    body: "See you there.",
    emails: ["a@example.com", "b@example.com"],
  });
  assert.equal(recipientCount, 2);
  assert.match(href, /^mailto:\?/);
  assert.ok(href.includes("bcc="));
  assert.ok(!/[?&]to=/.test(href));
  assert.ok(!/[?&]cc=/.test(href));
});

test("refuses to build a link that would exceed the mail client ceiling", () => {
  // Silently dropping recipients past the limit would send an announcement to
  // some attendees and quietly not to others, which is the same class of bug
  // as a CSV importer discarding columns without saying so.
  const { href, tooLong, recipientCount } = buildAnnouncementMailto({
    subject: "Schedule change",
    body: "Moved to room 2.",
    emails: many(200),
  });
  assert.equal(tooLong, true);
  assert.equal(href, null, "no href at all, so it cannot be used by accident");
  assert.equal(recipientCount, 200, "still reports how many there were");
});

test("builds a link for a list small enough to work", () => {
  const { href, tooLong } = buildAnnouncementMailto({
    subject: "Hi",
    body: "Short",
    emails: many(5),
  });
  assert.equal(tooLong, false);
  assert.ok(href.length <= MAILTO_SAFE_LENGTH);
});

test("deduplicates addresses case insensitively", () => {
  const { recipientCount, href } = buildAnnouncementMailto({
    emails: ["Ann@Example.com", "ann@example.com", "bob@example.com"],
  });
  assert.equal(recipientCount, 2);
  assert.ok(href.toLowerCase().includes("ann%40example.com"));
});

test("ignores blank and missing addresses", () => {
  const { recipientCount } = buildAnnouncementMailto({
    emails: ["a@example.com", "", null, undefined, "   "],
  });
  assert.equal(recipientCount, 1);
});

test("encodes subject and body so punctuation survives", () => {
  const { href } = buildAnnouncementMailto({
    subject: "Room 2 & 3",
    body: "Line one\nLine two — and a #hash",
    emails: ["a@example.com"],
  });
  assert.ok(href.includes("Room%202%20%26%203"));
  assert.ok(href.includes("%0A"), "newline preserved");
  assert.ok(href.includes("%23"), "hash encoded, not treated as a fragment");
});

test("still opens a blank compose window when there are no attendees yet", () => {
  const { href, tooLong, recipientCount } = buildAnnouncementMailto({
    subject: "Hello",
    body: "Body",
    emails: [],
  });
  assert.equal(recipientCount, 0);
  assert.equal(tooLong, false);
  assert.ok(href.startsWith("mailto:?"));
  assert.ok(!href.includes("bcc="), "no empty bcc parameter");
});

test("reports the address list separately so it can be copied when the link cannot be used", () => {
  const emails = many(200);
  const { bcc, recipientCount } = buildAnnouncementMailto({ emails });
  assert.equal(recipientCount, 200);
  assert.equal(bcc.split(",").length, 200, "every address available to copy");
});
