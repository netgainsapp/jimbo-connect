/**
 * Tests for the shared guest-list parser.
 *
 * Run with `npm test` in frontend/, which is `node --test` — deliberately no
 * test framework, because this repo has none and the parser is the one piece
 * of frontend logic where a silent mistake writes wrong data into a customer's
 * event rather than just looking wrong on screen.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { parsePaste, isLikelyEmail } from "./parseAttendeeCsv.js";

// ---------------------------------------------------------------------------
// Quoted fields (RFC 4180). Eventbrite, Meetup and Excel all quote any field
// containing the delimiter, so this is the ordinary case, not an exotic one.
// ---------------------------------------------------------------------------

test("keeps a quoted field that contains the delimiter intact", () => {
  const { rows, errors } = parsePaste(
    'email,name,company\njane@example.com,"Doe, Jane","Acme, Inc."',
  );
  assert.deepEqual(errors, []);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].name, "Doe, Jane");
  assert.equal(rows[0].company, "Acme, Inc.");
});

test("does not let a quoted delimiter shift later columns", () => {
  const { rows } = parsePaste(
    'email,name,company,industry\na@example.com,"Ray, Bob","Globex, LLC",Software',
  );
  assert.equal(rows[0].industry, "Software");
});

test("unescapes a doubled quote inside a quoted field", () => {
  const { rows } = parsePaste(
    'email,name,company\na@example.com,Ann,"The ""Big"" Company"',
  );
  assert.equal(rows[0].company, 'The "Big" Company');
});

test("keeps a record together when a quoted field contains a newline", () => {
  const { rows, errors } = parsePaste(
    'email,name,bio\na@example.com,Ann,"Line one\nLine two"\nb@example.com,Bob,Short',
  );
  assert.deepEqual(errors, []);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].bio, "Line one\nLine two");
  assert.equal(rows[1].email, "b@example.com");
});

test("ignores delimiters inside quotes when detecting the delimiter", () => {
  // Three commas inside quotes, one real semicolon separator.
  const { rows } = parsePaste('email;name\na@example.com;"Smith, Jr., Bob"');
  assert.equal(rows[0].name, "Smith, Jr., Bob");
});

test("strips surrounding quotes from an ordinary quoted field", () => {
  const { rows } = parsePaste('email,name\n"a@example.com","Ann Lee"');
  assert.equal(rows[0].email, "a@example.com");
  assert.equal(rows[0].name, "Ann Lee");
});

// ---------------------------------------------------------------------------
// Email validation. The server's EmailStr validates the whole list at once, so
// one bad address 422s the entire batch. Catching it per row here means the
// host is told which line is wrong instead of losing every good row with it.
// ---------------------------------------------------------------------------

test("reports a malformed address by line number instead of passing it through", () => {
  const { rows, errors } = parsePaste(
    "email,name\nnotanemail,Nobody\ngood@example.com,Good Row",
  );
  assert.equal(rows.length, 1);
  assert.equal(rows[0].email, "good@example.com");
  assert.equal(errors.length, 1);
  assert.equal(errors[0].line, 2);
  assert.match(errors[0].reason, /not a valid email/i);
});

test("keeps every valid row when one row in the middle is bad", () => {
  const { rows, errors } = parsePaste(
    [
      "email,name",
      "a@example.com,A",
      "b@example.com,B",
      "broken,C",
      "d@example.com,D",
    ].join("\n"),
  );
  assert.deepEqual(
    rows.map((r) => r.email),
    ["a@example.com", "b@example.com", "d@example.com"],
  );
  assert.equal(errors.length, 1);
  assert.equal(errors[0].line, 4);
});

test("accepts unusual but legal local parts rather than dropping a real guest", () => {
  // Rejecting these would silently skip a genuine attendee, which is worse
  // than forwarding them to the server, which is the real authority.
  for (const addr of [
    "o'brien@example.com",
    "first.last+tag@sub.example.co.uk",
    "a_b-c@example-host.com",
    "x!#$%&'*+-/=?^_`{|}~@example.com",
  ]) {
    assert.equal(isLikelyEmail(addr), true, `${addr} should be accepted`);
  }
});

test("rejects addresses that are clearly not addresses", () => {
  for (const addr of [
    "notanemail",
    "@example.com",
    "a@b",
    "a@@example.com",
    "two words@example.com",
    "a@example..com",
    "",
  ]) {
    assert.equal(isLikelyEmail(addr), false, `${addr} should be rejected`);
  }
});

// ---------------------------------------------------------------------------
// Regressions: everything that already worked must keep working.
// ---------------------------------------------------------------------------

test("still parses a plain unquoted comma file", () => {
  const { rows, errors } = parsePaste(
    "email,name,company\njane@example.com,Jane Doe,Acme\nbob@example.com,Bob Ray,Globex",
  );
  assert.deepEqual(errors, []);
  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0], {
    email: "jane@example.com",
    name: "Jane Doe",
    company: "Acme",
  });
});

test("still handles tab and semicolon delimiters", () => {
  assert.equal(parsePaste("email\tname\na@example.com\tAnn").rows[0].name, "Ann");
  assert.equal(parsePaste("email;name\na@example.com;Ann").rows[0].name, "Ann");
});

test("still reads Name <email> with no header row", () => {
  const { rows } = parsePaste(
    "Jane Doe <jane@example.com>\nBob Ray <bob@example.com>",
  );
  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0], { email: "jane@example.com", name: "Jane Doe" });
});

test("still maps header aliases", () => {
  const { rows } = parsePaste(
    "E-Mail,Full Name,Job Title,Organization\na@example.com,Ann Lee,VP,Acme",
  );
  assert.deepEqual(rows[0], {
    email: "a@example.com",
    name: "Ann Lee",
    role: "VP",
    company: "Acme",
  });
});

test("still enforces the ten digit phone rule and reformats valid numbers", () => {
  const { rows, errors } = parsePaste(
    [
      "email,name,phone",
      "a@example.com,A,(303) 555-0142",
      "b@example.com,B,+1 303 555 0144",
    ].join("\n"),
  );
  assert.equal(rows.length, 1);
  assert.equal(rows[0].phone, "303-555-0142");
  assert.equal(errors.length, 1);
  assert.match(errors[0].reason, /not 10 digits/);
});

test("still reports a row with no email at all", () => {
  const { rows, errors } = parsePaste("email,name\n,Blank\ngood@example.com,Good");
  assert.equal(rows.length, 1);
  assert.equal(errors.length, 1);
  assert.match(errors[0].reason, /No email found/);
});

test("ignores blank lines and a trailing newline", () => {
  const { rows, errors } = parsePaste(
    "email,name\na@example.com,A\n\n\nb@example.com,B\n",
  );
  assert.deepEqual(errors, []);
  assert.equal(rows.length, 2);
});

test("returns nothing for empty input", () => {
  assert.deepEqual(parsePaste(""), { rows: [], errors: [] });
  assert.deepEqual(parsePaste("   \n  \n"), { rows: [], errors: [] });
});

test("reports the true source line number when blank lines precede a bad row", () => {
  const { errors } = parsePaste("email,name\n\na@example.com,A\n\nbroken,B");
  assert.equal(errors.length, 1);
  assert.equal(errors[0].line, 5);
});
