/**
 * Tests for import source detection and the Audience Republic path.
 *
 * Run with `npm test` in frontend/, which is `node --test`.
 *
 * The header rows below are taken from Audience Republic's documented standard
 * and extended exports (Help Center, 2026-08-07). They are synthetic: no real
 * attendee data appears here, and no file from a live customer account was
 * available when these were written. If a genuine export ever turns up,
 * replace these strings with its header row.
 *
 * The test that matters most is the false positive one. Everything else can be
 * fixed after the fact; wrongly claiming a file is an Audience Republic export
 * applies another tool's phone rules to a spreadsheet that never asked for
 * them.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { detectSource, SOURCES, stripCustomFieldPrefix } from "./importSource.js";
import { parsePaste, analyzePaste, isIgnoredHeader } from "./parseAttendeeCsv.js";

const AR_STANDARD =
  "Email Address,First Name,Last Name,Mobile Number,Country,State,City," +
  "Postcode,Date of Birth,Gender,Email Opt-In,SMS Opt-In,Tags";

const AR_EXTENDED =
  AR_STANDARD +
  ",Custom Field - Company,Custom Field - Job Title,Total Campaign Count," +
  "Total Event Count,Total Referrals,Total Tickets,Total Points,Total Ticket Sales";

const AR_ROW =
  "ava.reynolds@example.com,Ava,Reynolds,+1 303-555-0101,United States,CO," +
  "Denver,80202,1987-04-14,Female,Yes,Yes,VIP; Founder; Denver";

const AR_ROW_EXTENDED = AR_ROW + ",Trailhead Labs,Founder & CEO,1,2,0,1,0,79.00";

// ---------------------------------------------------------------------------
// Detection
// ---------------------------------------------------------------------------

test("recognises a standard Audience Republic export", () => {
  const { source } = detectSource(AR_STANDARD.split(","));
  assert.equal(source, SOURCES.AUDIENCE_REPUBLIC);
});

test("recognises an extended Audience Republic export", () => {
  const { source, signals } = detectSource(AR_EXTENDED.split(","));
  assert.equal(source, SOURCES.AUDIENCE_REPUBLIC);
  assert.ok(signals.includes("custom field prefix"));
});

test("does not call a generic spreadsheet Audience Republic", () => {
  const { source } = detectSource(["Email", "Name", "Company"]);
  assert.equal(source, SOURCES.GENERIC_CSV);
});

test("one shared column is never enough on its own", () => {
  // "Email Address" and "Tags" both appear in plenty of unrelated exports.
  const { source } = detectSource(["Email Address", "Notes"]);
  assert.equal(source, SOURCES.GENERIC_CSV);
});

test("a promising filename cannot carry a file with no matching columns", () => {
  const { source } = detectSource(
    ["Email", "Name"],
    "audience-republic-export-final.csv",
  );
  assert.equal(source, SOURCES.GENERIC_CSV);
});

test("recognises an Eventbrite export and does not confuse it for AR", () => {
  const { source } = detectSource([
    "Order #",
    "Order Date",
    "First Name",
    "Last Name",
    "Email",
    "Ticket Type",
    "Attendee Status",
  ]);
  assert.equal(source, SOURCES.EVENTBRITE);
});

test("an empty header row is unknown rather than a guess", () => {
  assert.equal(detectSource([]).source, SOURCES.UNKNOWN);
});

test("header normalisation is case and punctuation insensitive", () => {
  const { source } = detectSource([
    "EMAIL_OPT_IN",
    "sms opt-in",
    "Total  Points",
  ]);
  assert.equal(source, SOURCES.AUDIENCE_REPUBLIC);
});

// ---------------------------------------------------------------------------
// Custom field prefix
// ---------------------------------------------------------------------------

test("strips the Audience Republic custom field prefix", () => {
  assert.equal(stripCustomFieldPrefix("Custom Field - Company"), "company");
  assert.equal(stripCustomFieldPrefix("Custom Field: Job Title"), "job title");
  assert.equal(stripCustomFieldPrefix("Company"), "company");
});

test("maps company and job title out of custom field columns", () => {
  const { rows } = parsePaste([AR_EXTENDED, AR_ROW_EXTENDED].join("\n"), {
    source: SOURCES.AUDIENCE_REPUBLIC,
  });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].company, "Trailhead Labs");
  assert.equal(rows[0].role, "Founder & CEO");
});

// ---------------------------------------------------------------------------
// Phone. This is the bug that would have silently emptied a real import.
// ---------------------------------------------------------------------------

test("keeps a US number that arrives with a country code and dashes", () => {
  const { rows, errors } = parsePaste([AR_STANDARD, AR_ROW].join("\n"), {
    source: SOURCES.AUDIENCE_REPUBLIC,
  });
  assert.deepEqual(errors, []);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].phone, "303-555-0101");
});

test("keeps the attendee when the number is not a US one", () => {
  const { rows, errors } = parsePaste(
    [AR_STANDARD, AR_ROW.replace("+1 303-555-0101", "+61 412 345 678")].join("\n"),
    { source: SOURCES.AUDIENCE_REPUBLIC },
  );
  assert.deepEqual(errors, []);
  assert.equal(rows.length, 1, "the person is not lost with the number");
  assert.ok(!rows[0].phone, "the unusable number is dropped, not stored");
  assert.equal(rows[0].email, "ava.reynolds@example.com");
});

test("an empty mobile column is not an error", () => {
  const { rows, errors } = parsePaste(
    [AR_STANDARD, AR_ROW.replace("+1 303-555-0101", "")].join("\n"),
    { source: SOURCES.AUDIENCE_REPUBLIC },
  );
  assert.deepEqual(errors, []);
  assert.equal(rows.length, 1);
});

test("a generic spreadsheet keeps the stricter ten digit rule", () => {
  // Unchanged behaviour: without a recognised source an eleven digit number is
  // likelier to be a typo than a country code, and the row is refused.
  const { rows, errors } = parsePaste("email,name,phone\na@example.com,A,+1 303 555 0144");
  assert.equal(rows.length, 0);
  assert.match(errors[0].reason, /not 10 digits/);
});

// ---------------------------------------------------------------------------
// Privacy. Consent belongs to Audience Republic; it does not transfer.
// ---------------------------------------------------------------------------

test("marketing consent, date of birth and gender never enter a row", () => {
  const { rows } = parsePaste([AR_EXTENDED, AR_ROW_EXTENDED].join("\n"), {
    source: SOURCES.AUDIENCE_REPUBLIC,
  });
  const row = rows[0];
  const serialised = JSON.stringify(row);
  for (const forbidden of ["Yes", "1987-04-14", "Female"]) {
    assert.ok(
      !serialised.includes(forbidden),
      `imported row must not carry ${forbidden}`,
    );
  }
  assert.ok(!("gender" in row));
  assert.ok(!("date_of_birth" in row));
  assert.ok(!("email_opt_in" in row));
});

test("lifetime CRM counters are ignored rather than mapped", () => {
  for (const h of [
    "Email Opt-In",
    "SMS Opt-In",
    "Date of Birth",
    "Gender",
    "Total Ticket Sales",
    "Total Points",
  ]) {
    assert.ok(isIgnoredHeader(h), `${h} should be ignored`);
  }
});

// ---------------------------------------------------------------------------
// Review screen
// ---------------------------------------------------------------------------

test("analyze reports source, mapped, unmapped and ignored columns", () => {
  const out = analyzePaste([AR_EXTENDED, AR_ROW_EXTENDED].join("\n"), "export.csv");
  assert.equal(out.source, SOURCES.AUDIENCE_REPUBLIC);
  assert.equal(out.rows.length, 1);

  const mappedFields = out.mapped.map((m) => m.field);
  for (const f of ["email", "first_name", "last_name", "phone", "company", "role"]) {
    assert.ok(mappedFields.includes(f), `expected ${f} to be mapped`);
  }
  // Location columns are real data we simply have nowhere to put.
  assert.ok(out.unmapped.some((h) => /postcode/i.test(h)));
  // And consent is listed as deliberately ignored, not silently swallowed.
  assert.ok(out.ignored.some((h) => /opt-in/i.test(h)));
});

test("analyze does not claim a source for a hand built list", () => {
  const out = analyzePaste("email,name\na@example.com,Ann");
  assert.equal(out.source, SOURCES.GENERIC_CSV);
  assert.equal(out.rows.length, 1);
});

test("first and last name are joined into the single stored name", () => {
  const { rows } = parsePaste([AR_STANDARD, AR_ROW].join("\n"), {
    source: SOURCES.AUDIENCE_REPUBLIC,
  });
  assert.equal(rows[0].name, "Ava Reynolds");
  assert.ok(!("first_name" in rows[0]));
});

test("a hyphenated surname and an apostrophe survive intact", () => {
  const rows = parsePaste(
    [
      AR_STANDARD,
      AR_ROW.replace("Ava,Reynolds", "Zoe,Martin-Smith"),
      AR_ROW.replace("ava.reynolds@example.com,Ava,Reynolds", "liam@example.com,Liam,O'Neill"),
    ].join("\n"),
    { source: SOURCES.AUDIENCE_REPUBLIC },
  ).rows;
  assert.equal(rows[0].name, "Zoe Martin-Smith");
  assert.equal(rows[1].name, "Liam O'Neill");
});

test("semicolons inside the Tags column do not become the delimiter", () => {
  // Tags arrive as "VIP; Founder; Denver" inside a comma separated file. If
  // the semicolon won the delimiter vote every row would shred.
  const { rows, errors } = parsePaste([AR_STANDARD, AR_ROW].join("\n"), {
    source: SOURCES.AUDIENCE_REPUBLIC,
  });
  assert.deepEqual(errors, []);
  assert.equal(rows[0].email, "ava.reynolds@example.com");
  assert.equal(rows[0].name, "Ava Reynolds");
});

// ---------------------------------------------------------------------------
// Manual remapping. Automatic mapping is a good guess; the host is the one
// looking at the file, so they get the last word.
// ---------------------------------------------------------------------------

test("a host can point a column at a different field", () => {
  const { rows } = parsePaste(
    ["Email Address,Notes", "ava@example.com,Runs the Denver chapter"].join("\n"),
    { overrides: { notes: "bio" } },
  );
  assert.equal(rows[0].bio, "Runs the Denver chapter");
});

test("a host can switch a mapped column off", () => {
  const { rows } = parsePaste(
    [AR_EXTENDED, AR_ROW_EXTENDED].join("\n"),
    { source: SOURCES.AUDIENCE_REPUBLIC, overrides: { "custom field company": null } },
  );
  assert.equal(rows.length, 1);
  assert.ok(!rows[0].company, "company was switched off and must not be stored");
  assert.equal(rows[0].role, "Founder & CEO", "other columns are unaffected");
});

test("an override is matched however the header was spelled", () => {
  const { rows } = parsePaste(
    ["Email Address,Job_Title", "ava@example.com,Founder"].join("\n"),
    { overrides: { "job title": "industry" } },
  );
  assert.equal(rows[0].industry, "Founder");
  assert.ok(!rows[0].role);
});

test("analyze reflects an override in the mapping it reports", () => {
  const out = analyzePaste(
    ["Email Address,Notes", "ava@example.com,x"].join("\n"),
    "",
    { notes: "bio" },
  );
  assert.ok(out.mapped.some((m) => m.header === "Notes" && m.field === "bio"));
  assert.ok(!out.unmapped.includes("Notes"));
});

test("a switched off column is listed as not imported, not as a privacy exclusion", () => {
  const out = analyzePaste(
    ["Email Address,Company", "ava@example.com,Acme"].join("\n"),
    "",
    { company: null },
  );
  assert.ok(out.unmapped.includes("Company"));
  assert.ok(!out.ignored.includes("Company"));
});

test("overrides cannot be used to import a column we exclude on purpose", () => {
  // The exclusion is ours, not a default the host can toggle: consent given to
  // another company is not consent given to us, whatever the mapping says.
  const out = analyzePaste([AR_EXTENDED, AR_ROW_EXTENDED].join("\n"));
  assert.ok(out.ignored.some((h) => /opt-in/i.test(h)));
});
