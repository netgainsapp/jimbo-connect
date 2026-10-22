/**
 * Event Leads page logic. node --test cannot parse JSX, so the brief's render
 * tests run against the pure helpers the page renders from (ruling R3).
 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  sortLeads,
  visibleLeads,
  approveDisabled,
  approveLabel,
  approveOutcome,
  kpiRows,
  drawerSections,
  funnelSteps,
  contactSummary,
  statusBadge,
  parseScoreInput,
} from "./eventLeads.js";

const NOW = new Date("2026-10-22T18:00:00Z");

function lead(id, tier, start, extra = {}) {
  return {
    id,
    status: "new",
    anchor: { title: `Event ${id}`, start },
    score: { tier, score: 70, reason: "Recurring founder dinner." },
    contact: { name: "", email: "", linkedin_url: "" },
    signal_scout: {},
    funnel: {},
    ...extra,
  };
}

test("rows sort tier A first, then by days until, with archived leads last", () => {
  const leads = [
    lead("b-soon", "B", "2026-10-24T01:00:00Z"),
    lead("a-late", "A", "2026-11-20T01:00:00Z"),
    lead("a-archived", "A", "2026-10-23T01:00:00Z", { status: "archived" }),
    lead("a-soon", "A", "2026-10-30T01:00:00Z"),
    lead("a-undated", "A", null),
  ];
  const ids = sortLeads(leads, NOW).map((l) => l.id);
  assert.deepEqual(ids, ["a-soon", "a-late", "a-undated", "b-soon", "a-archived"]);
});

test("sorting does not reorder the caller's array", () => {
  const leads = [lead("b", "B", "2026-10-24T01:00:00Z"), lead("a", "A", "2026-11-20T01:00:00Z")];
  sortLeads(leads, NOW);
  assert.deepEqual(leads.map((l) => l.id), ["b", "a"]);
});

test("tier C rows stay hidden until the toggle is on", () => {
  const leads = [lead("a", "A", null), lead("c", "C", null), lead("b", "B", null)];
  assert.deepEqual(visibleLeads(leads, { showC: false }).map((l) => l.id), ["a", "b"]);
  assert.deepEqual(visibleLeads(leads, { showC: true }).map((l) => l.id), ["a", "c", "b"]);
});

test("Approve is disabled for an existing customer and an archived lead", () => {
  const customer = lead("x", "A", null, { status: "existing_customer" });
  const archived = lead("y", "A", null, { status: "archived" });
  assert.equal(approveDisabled(customer), true);
  assert.equal(approveLabel(customer), "Existing customer");
  assert.equal(approveDisabled(archived), true);
  assert.equal(approveLabel(archived), "Archived");
});

test("Approve stays available for a new lead and offers a retry when outreach failed", () => {
  const fresh = lead("n", "A", null);
  assert.equal(approveDisabled(fresh), false);
  assert.equal(approveLabel(fresh), "Approve");

  const failed = lead("f", "A", null, {
    status: "approved",
    signal_scout: { error: "Signal Scout push failed" },
  });
  assert.equal(approveDisabled(failed), false);
  assert.equal(approveLabel(failed), "Retry outreach");

  const done = lead("d", "A", null, { status: "approved", signal_scout: { prospect_id: "p1" } });
  assert.equal(approveDisabled(done), true);
  assert.equal(approveLabel(done), "Approved");
  assert.equal(approveDisabled({ ...done, status: "claimed" }), true);
});

test("an approve answer with a Signal Scout error is reported as an error", () => {
  const ok = approveOutcome({ status: "approved", signal_scout: { prospect_id: "p1" } });
  assert.equal(ok.type, "success");
  const failed = approveOutcome({ status: "approved", signal_scout: { error: "timeout" } });
  assert.equal(failed.type, "error");
  assert.match(failed.message, /timeout/);
});

test("the drawer shows the reason block and the email preview", () => {
  const detail = lead("d", "A", "2026-10-30T01:00:00Z", {
    anchor: {
      title: "Founder Dinner",
      start: "2026-10-30T01:00:00Z",
      description: "Monthly dinner.",
      source_url: "https://example.com/e/1",
    },
    email_preview: { subject: "Your Founder Dinner guest list", body: "Hi Jane" },
    linkedin_preview: { note: "Hi", followup: "Following up" },
  });
  const sections = drawerSections(detail);
  assert.deepEqual(sections, [
    "reason",
    "description",
    "contact",
    "score",
    "email_preview",
    "linkedin_preview",
    "funnel",
  ]);
});

test("the drawer leaves out the reason and previews it has nothing for", () => {
  const bare = lead("b", "A", null, { score: { tier: "A", score: 70 } });
  assert.deepEqual(drawerSections(bare), ["contact", "score", "funnel"]);
});

test("the funnel timeline lists every step in order with the stamps reached", () => {
  const steps = funnelSteps(
    lead("f", "A", null, {
      funnel: { found_at: "2026-10-20T00:00:00Z", approved_at: "2026-10-21T00:00:00Z" },
    }),
  );
  assert.deepEqual(
    steps.map((s) => s.key),
    [
      "found", "scored", "approved", "emailed", "opened", "clicked",
      "claimed", "attendees_uploaded", "event_passed", "converted",
    ],
  );
  assert.equal(steps[0].at, "2026-10-20T00:00:00Z");
  assert.equal(steps[1].at, null);
  assert.equal(steps[2].at, "2026-10-21T00:00:00Z");
});

test("a lead with no email and no LinkedIn reads as none found", () => {
  assert.equal(contactSummary(lead("n", "A", null)), "none found");
  const reachable = lead("r", "A", null, {
    contact: { name: "Jane Doe", email: "jane@example.com", linkedin_url: "" },
  });
  assert.match(contactSummary(reachable), /Jane Doe/);
  assert.match(contactSummary(reachable), /jane@example.com/);
});

test("status badges name the state and flag failed outreach", () => {
  assert.deepEqual(statusBadge(lead("n", "A", null)), { label: "New", tone: "neutral" });
  assert.equal(statusBadge(lead("c", "A", null, { status: "existing_customer" })).label, "Existing customer");
  const failed = statusBadge(
    lead("f", "A", null, { status: "approved", signal_scout: { error: "x" } }),
  );
  assert.equal(failed.tone, "error");
});

test("the KPI strip always renders five weeks, newest first, padding with zeros", () => {
  const rows = kpiRows([
    { week: "2026-10-12", ingested: 30, qualification_rate: 0.4, approved: 3 },
    { week: "2026-10-19", ingested: 40, qualification_rate: 0.5, approved: 5 },
  ]);
  assert.equal(rows.length, 5);
  assert.deepEqual(
    rows.map((r) => r.week),
    ["2026-10-19", "2026-10-12", "2026-10-05", "2026-09-28", "2026-09-21"],
  );
  assert.equal(rows[0].ingested, 40);
  assert.equal(rows[0].emailed, 0);
  assert.equal(rows[4].ingested, 0);
  assert.equal(rows[4].qualification_rate, 0);
  assert.equal(kpiRows(undefined).length, 5);
});

test("score inputs accept a whole number from 0 to 100, and blank only where allowed", () => {
  assert.deepEqual(parseScoreInput("85"), { ok: true, value: 85 });
  assert.deepEqual(parseScoreInput("", { allowBlank: true }), { ok: true, value: null });
  assert.equal(parseScoreInput("").ok, false);
  assert.equal(parseScoreInput("101").ok, false);
  assert.equal(parseScoreInput("7.5").ok, false);
});
