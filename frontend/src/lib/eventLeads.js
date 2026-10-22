/**
 * Pure logic for the admin Event Leads page (AdminEventLeads.jsx and
 * EventLeadDrawer.jsx). Kept out of the JSX so `node --test` can cover it.
 *
 * The server already sorts and filters the list; the sort and the tier C
 * filter here are defensive copies that agree with
 * backend/event_leads_rules.py `tier_sort_key` and routers/event_leads.py.
 */

const DENVER = "America/Denver";
const MS_PER_DAY = 24 * 60 * 60 * 1000;
const DAYS_PER_WEEK = 7;
const TIER_RANK = { A: 0, B: 1, C: 2 };
const UNKNOWN_TIER_RANK = 3;
// Sorts an undated lead after every dated lead of its tier (NO_DATE_DAYS).
const NO_DATE_DAYS = 10 ** 6;
const MAX_SCORE = 100;
const PERCENT = 100;

export const KPI_WEEKS = 5;
// LinkedIn caps a connection note at 300 characters (event_leads_copy.py).
export const LINKEDIN_NOTE_MAX = 300;

export const KPI_METRICS = [
  { key: "ingested", label: "Ingested" },
  { key: "qualification_rate", label: "Qualification rate", percent: true },
  { key: "approved", label: "Approved" },
  { key: "emailed", label: "Emailed" },
  { key: "opened", label: "Opened" },
  { key: "clicked", label: "Claim link clicked" },
  { key: "claimed", label: "Claimed" },
  { key: "attendees_uploaded", label: "Attendees uploaded" },
  { key: "converted", label: "Converted" },
];

export const FUNNEL_STEPS = [
  { key: "found", label: "Found" },
  { key: "scored", label: "Scored" },
  { key: "approved", label: "Approved" },
  { key: "emailed", label: "Emailed" },
  { key: "opened", label: "Opened" },
  { key: "clicked", label: "Claim link clicked" },
  { key: "claimed", label: "Claimed" },
  { key: "attendees_uploaded", label: "Attendees uploaded" },
  { key: "event_passed", label: "Event passed" },
  { key: "converted", label: "Converted" },
];

const STATUS_BADGES = {
  new: { label: "New", tone: "neutral" },
  approved: { label: "Approved", tone: "success" },
  claimed: { label: "Claimed", tone: "success" },
  archived: { label: "Archived", tone: "muted" },
  unreachable: { label: "Unreachable", tone: "warning" },
  existing_customer: { label: "Existing customer", tone: "info" },
};

const APPROVED_STATUSES = new Set(["approved", "claimed"]);
const LOCKED_STATUSES = new Set(["existing_customer", "archived", "claimed"]);

// ---------- dates ----------

const denverDay = new Intl.DateTimeFormat("en-CA", {
  timeZone: DENVER,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

function dayNumber(date) {
  const parts = Object.fromEntries(
    denverDay.formatToParts(date).map((p) => [p.type, p.value]),
  );
  const utc = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day));
  return utc / MS_PER_DAY;
}

/** Whole Denver calendar days from `now` to the ISO instant `iso`, or null. */
export function daysUntil(iso, now = new Date()) {
  if (!iso) return null;
  const target = new Date(iso);
  if (Number.isNaN(target.getTime())) return null;
  return dayNumber(target) - dayNumber(now);
}

/** Days until the lead's anchor event, re-computed on render, else the server's. */
export function leadDays(lead, now = new Date()) {
  const days = daysUntil(lead?.anchor?.start, now);
  if (days !== null) return days;
  return Number.isInteger(lead?.days_until) ? lead.days_until : null;
}

export function daysUntilLabel(days) {
  if (days === null || days === undefined) return "";
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "yesterday";
  return days > 0 ? `in ${days} days` : `${-days} days ago`;
}

/** The anchor start in the event's own time zone. */
export function eventDateLabel(lead) {
  const start = lead?.anchor?.start;
  const date = start ? new Date(start) : null;
  if (!date || Number.isNaN(date.getTime())) return "No date";
  const options = {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  };
  try {
    return date.toLocaleString(undefined, {
      ...options,
      timeZone: lead.anchor.timezone || DENVER,
    });
  } catch {
    // An unknown zone name throws a RangeError; Denver is the engine's home.
    return date.toLocaleString(undefined, { ...options, timeZone: DENVER });
  }
}

// ---------- links ----------

const SAFE_PROTOCOLS = new Set(["http:", "https:"]);

/**
 * A scraped URL (source listing, organizer site, LinkedIn, website) when it is
 * an absolute http or https URL, else null. React renders a `javascript:` href
 * as given, so every scraped link must pass through here before it is a link.
 */
export function safeHttpUrl(value) {
  const text = typeof value === "string" ? value.trim() : "";
  if (!text) return null;
  try {
    return SAFE_PROTOCOLS.has(new URL(text).protocol) ? text : null;
  } catch {
    // Relative or malformed: not a link we render.
    return null;
  }
}

// ---------- list ----------

function sortKey(lead, now) {
  const rank = TIER_RANK[lead?.score?.tier] ?? UNKNOWN_TIER_RANK;
  const days = leadDays(lead, now);
  return [lead?.status === "archived" ? 1 : 0, rank, days ?? NO_DATE_DAYS];
}

function compareKeys(a, b) {
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) return a[i] - b[i];
  }
  return 0;
}

/** Tier A first, then days until ascending, archived last. A new array. */
export function sortLeads(leads, now = new Date()) {
  return (leads || [])
    .map((lead) => ({ lead, key: sortKey(lead, now) }))
    .sort((a, b) => compareKeys(a.key, b.key))
    .map(({ lead }) => lead);
}

export function visibleLeads(leads, { showC = false } = {}) {
  return (leads || []).filter((lead) => showC || lead?.score?.tier !== "C");
}

export function categoryLabel(lead) {
  const { format, vertical } = lead?.score || {};
  return [format, vertical].filter(Boolean).join(", ") || "Uncategorized";
}

/** "A 82", or with an override "A 90 (Claude 82)". The Claude score stays. */
export function scoreLabel(lead) {
  const { tier = "?", score } = lead?.score || {};
  const override = lead?.score_override;
  if (Number.isInteger(override)) return `${tier} ${override} (Claude ${score ?? "none"})`;
  return `${tier} ${score ?? ""}`.trim();
}

export function contactSummary(lead) {
  const { name, email, linkedin_url: linkedin } = lead?.contact || {};
  if (!email && !linkedin) return "none found";
  return [name, email, linkedin ? "LinkedIn" : ""].filter(Boolean).join(", ");
}

// ---------- approve ----------

/** Approved, Signal Scout refused the push, and no prospect exists yet. */
export function needsRetry(lead) {
  const scout = lead?.signal_scout || {};
  return lead?.status === "approved" && Boolean(scout.error) && !scout.prospect_id;
}

export function approveDisabled(lead) {
  if (LOCKED_STATUSES.has(lead?.status)) return true;
  return lead?.status === "approved" && Boolean(lead?.signal_scout?.prospect_id);
}

export function approveLabel(lead) {
  if (lead?.status === "existing_customer") return "Existing customer";
  if (lead?.status === "archived") return "Archived";
  if (needsRetry(lead)) return "Retry outreach";
  if (APPROVED_STATUSES.has(lead?.status)) return "Approved";
  return "Approve";
}

/** Toast for an approve or retry answer. */
export function approveOutcome(res) {
  const scout = res?.signal_scout || {};
  if (scout.error) {
    return {
      type: "error",
      message: `Approved, but outreach failed: ${scout.error}. Use Retry outreach.`,
    };
  }
  if (scout.prospect_id) {
    return { type: "success", message: "Approved. Signal Scout has the lead." };
  }
  return {
    type: "success",
    message: "Approved. There is no email on file, so LinkedIn is the only channel.",
  };
}

// ---------- status and funnel ----------

export function funnelSteps(lead) {
  const funnel = lead?.funnel || {};
  return FUNNEL_STEPS.map(({ key, label }) => ({
    key,
    label,
    at: funnel[`${key}_at`] || null,
  }));
}

/** Status label, or for an approved lead the furthest funnel step past approval. */
export function statusBadge(lead) {
  if (needsRetry(lead)) return { label: "Outreach failed", tone: "error" };
  const fallback = { label: lead?.status || "Unknown", tone: "neutral" };
  const base = STATUS_BADGES[lead?.status] || fallback;
  if (!APPROVED_STATUSES.has(lead?.status)) return base;
  const steps = funnelSteps(lead);
  const afterApproval = steps.slice(steps.findIndex((s) => s.key === "approved") + 1);
  const furthest = afterApproval.filter((s) => s.at).pop();
  return furthest ? { label: furthest.label, tone: base.tone } : base;
}

export function drawerSections(lead) {
  const anchor = lead?.anchor || {};
  const preview = lead?.email_preview;
  const present = {
    reason: Boolean(lead?.score?.reason),
    description: Boolean(anchor.description || anchor.source_url),
    contact: true,
    score: true,
    email_preview: Boolean(preview && (preview.subject || preview.body)),
    linkedin_preview: Boolean(lead?.linkedin_preview),
    funnel: true,
  };
  return Object.keys(present).filter((key) => present[key]);
}

// ---------- KPI strip ----------

function weekBefore(week) {
  if (!week) return null;
  const date = new Date(`${week}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return null;
  return new Date(date.getTime() - DAYS_PER_WEEK * MS_PER_DAY).toISOString().slice(0, 10);
}

function kpiRow(row, week) {
  const out = { week };
  for (const { key } of KPI_METRICS) {
    const value = row?.[key];
    out[key] = typeof value === "number" && Number.isFinite(value) ? value : 0;
  }
  return out;
}

/** Exactly KPI_WEEKS rows, newest first; missing weeks are zeros. */
export function kpiRows(kpis) {
  const rows = (Array.isArray(kpis) ? kpis : [])
    .filter((row) => row && typeof row.week === "string")
    .sort((a, b) => b.week.localeCompare(a.week))
    .slice(0, KPI_WEEKS)
    .map((row) => kpiRow(row, row.week));
  while (rows.length < KPI_WEEKS) {
    rows.push(kpiRow(null, weekBefore(rows[rows.length - 1]?.week)));
  }
  return rows;
}

export function formatKpi(metric, value) {
  return metric.percent ? `${Math.round(value * PERCENT)}%` : String(value);
}

export function weekLabel(week) {
  if (!week) return "Earlier";
  const date = new Date(`${week}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return week;
  const day = date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
  return `Week of ${day}`;
}

// ---------- inputs and imports ----------

/** A whole score from 0 to 100. Blank is null where `allowBlank` (auto-approve off). */
export function parseScoreInput(text, { allowBlank = false } = {}) {
  const value = String(text ?? "").trim();
  if (value === "") {
    return allowBlank
      ? { ok: true, value: null }
      : { ok: false, error: "Enter a score from 0 to 100." };
  }
  if (!/^\d+$/.test(value) || Number(value) > MAX_SCORE) {
    return { ok: false, error: "Enter a whole number from 0 to 100." };
  }
  return { ok: true, value: Number(value) };
}

/** Toast for a Linked Helper results import. */
export function linkedinResultSummary(res) {
  const unknown = res?.unknown || [];
  const errors = res?.errors || [];
  const parts = [
    `${res?.updated ?? 0} updated`,
    `${res?.unchanged ?? 0} unchanged`,
    `${unknown.length} not matched to a lead`,
  ];
  if (errors.length) parts.push(`${errors.length} with errors`);
  return { type: errors.length ? "error" : "success", message: `${parts.join(", ")}.` };
}
