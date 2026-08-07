/**
 * Work out which tool a guest list came out of, from its header row.
 *
 * The point is not classification for its own sake: knowing the source lets
 * the importer apply the one or two rules that source needs (Audience Republic
 * puts a country code on every mobile, and prefixes custom columns) without
 * loosening those rules for everybody else.
 *
 * The hard requirement is the false positive. Calling a generic spreadsheet
 * "Audience Republic" would apply another tool's quirks to a file that does
 * not have them, so every source needs at least two distinctive headers before
 * it is claimed. "Email" is present in essentially every export ever made and
 * on its own proves nothing.
 *
 * A filename is supporting evidence only. Hosts rename downloads constantly,
 * and "audience-republic-final-FINAL.csv" is as likely to be a hand-built
 * spreadsheet as an export.
 *
 * Field names verified against Audience Republic's Help Center, 2026-08-07:
 * https://intercom.help/audiencerepublic/en/articles/11273947-export-contacts-from-audience-manager
 * https://intercom.help/audiencerepublic/en/articles/11188196-how-to-export-event-attendees
 */

export const SOURCES = {
  AUDIENCE_REPUBLIC: "audience_republic",
  EVENTBRITE: "eventbrite",
  GENERIC_CSV: "generic_csv",
  UNKNOWN: "unknown",
};

/** Lowercase, collapse punctuation and spacing, so "Email Opt-In",
 * "email_opt_in" and "Email OptIn" are one thing. */
export function normalizeHeader(h) {
  return String(h ?? "")
    .toLowerCase()
    .replace(/[\s_\-.]+/g, " ")
    .trim();
}

/** Columns an organizer added themselves arrive as "Custom Field - Company".
 * The prefix is Audience Republic's, the name after it is the host's. */
export const CUSTOM_FIELD_PREFIX = /^custom field\s*[-:]?\s*/;

export function stripCustomFieldPrefix(header) {
  const n = normalizeHeader(header);
  return n.replace(CUSTOM_FIELD_PREFIX, "").trim();
}

// Headers that essentially only Audience Republic emits. The opt-in pair and
// the "total *" counters are the strongest: they are CRM lifetime metrics, not
// anything a ticketing export or a hand-built list carries.
const AUDIENCE_REPUBLIC_SIGNALS = [
  "email opt in",
  "sms opt in",
  "total campaign count",
  "total event count",
  "total referrals",
  "total tickets",
  "total points",
  "total ticket sales",
  "postcode",
  "date of birth",
];

// Weaker on their own but corroborating in combination.
const AUDIENCE_REPUBLIC_WEAK = ["tags", "gender", "mobile number", "email address"];

const EVENTBRITE_SIGNALS = [
  "order",
  "order id",
  "order date",
  "ticket type",
  "attendee status",
  "event name",
  "barcode",
  "order type",
];

/**
 * Classify a header row.
 *
 * `headers` is the raw first record; `filename` is optional and only ever
 * breaks a tie. Returns one of SOURCES plus the evidence, so the review screen
 * can show the host why we think what we think rather than asserting it.
 */
export function detectSource(headers, filename = "") {
  const seen = (headers || []).map(normalizeHeader).filter(Boolean);
  if (seen.length === 0) return { source: SOURCES.UNKNOWN, signals: [], confidence: 0 };

  const hasCustomFieldPrefix = seen.some((h) => CUSTOM_FIELD_PREFIX.test(h));

  const arStrong = AUDIENCE_REPUBLIC_SIGNALS.filter((s) => seen.includes(s));
  const arWeak = AUDIENCE_REPUBLIC_WEAK.filter((s) => seen.includes(s));
  const ebStrong = EVENTBRITE_SIGNALS.filter((s) => seen.includes(s));

  // The prefix is close to a fingerprint, but it still only counts as one
  // signal so that a spreadsheet with a literal "Custom Field - X" column
  // cannot be claimed on that alone.
  const arScore = arStrong.length + (hasCustomFieldPrefix ? 1 : 0);

  const nameHint = /audience[\s_-]*republic/i.test(String(filename || ""));

  // Two distinctive headers is the floor for any claim. Below that the file is
  // a spreadsheet that happens to share a column name, and treating it as an
  // export would apply rules it never asked for.
  if (arScore >= 2 && arScore > ebStrong.length) {
    return {
      source: SOURCES.AUDIENCE_REPUBLIC,
      signals: [...arStrong, ...(hasCustomFieldPrefix ? ["custom field prefix"] : [])],
      confidence: Math.min(1, (arScore + arWeak.length) / 6),
    };
  }
  if (ebStrong.length >= 2 && ebStrong.length > arScore) {
    return {
      source: SOURCES.EVENTBRITE,
      signals: ebStrong,
      confidence: Math.min(1, ebStrong.length / 4),
    };
  }
  // One strong signal plus a matching filename is the only place the name is
  // allowed to matter, and it still needs real evidence in the file itself.
  if (arScore === 1 && nameHint) {
    return {
      source: SOURCES.AUDIENCE_REPUBLIC,
      signals: [...arStrong, "filename"],
      confidence: 0.4,
    };
  }

  // Something parseable, just not a tool we recognise. Still importable.
  if (seen.some((h) => h.includes("email") || h.includes("mail"))) {
    return { source: SOURCES.GENERIC_CSV, signals: [], confidence: 0 };
  }
  return { source: SOURCES.UNKNOWN, signals: [], confidence: 0 };
}

/**
 * Sources whose numbers carry a country code, so the importer should reduce
 * them rather than reject the row. Kept as a list rather than a boolean on the
 * call site so adding a source is one edit here.
 */
export function usesInternationalPhone(source) {
  return source === SOURCES.AUDIENCE_REPUBLIC;
}
