/**
 * Parse a pasted or uploaded guest list into import rows.
 *
 * Extracted from BulkImportModal so the admin importer and the host importer
 * read spreadsheets identically. Two parsers would drift, and the drift would
 * show up as "the same file works for Jim and not for a customer".
 *
 * Handles tab, comma and semicolon delimiters, a header row or none, RFC 4180
 * quoting, and "Name <email@host>" in a single column. Bad rows are returned as
 * errors with their line number rather than silently dropped.
 */
import { formatPhone, isValidPhone } from "./phone.js";

export const KNOWN_FIELDS = [
  "email",
  "name",
  "role",
  "company",
  "industry",
  "bio",
  "looking_for",
  "phone",
  "linkedin",
];

// Ticketing tools split the name in two. Eventbrite exports "First Name" and
// "Last Name" as separate columns, and before these were recognised an
// Eventbrite export imported every address with no name attached, filling the
// directory with rows that were just email addresses. These two are joined into
// `name` after mapping; they are never stored on their own.
const FIRST_NAME_ALIASES = [
  "first name",
  "firstname",
  "first_name",
  "given name",
  "givenname",
  "first",
];
const LAST_NAME_ALIASES = [
  "last name",
  "lastname",
  "last_name",
  "surname",
  "family name",
  "familyname",
  "last",
];

const HEADER_ALIASES = {
  email: ["email", "e-mail", "mail", "email address", "attendee email"],
  name: ["name", "full name", "fullname", "full_name", "attendee name"],
  first_name: FIRST_NAME_ALIASES,
  last_name: LAST_NAME_ALIASES,
  role: ["role", "title", "position", "job title", "jobtitle"],
  company: ["company", "organization", "org", "employer"],
  industry: ["industry", "sector"],
  bio: ["bio", "about"],
  looking_for: ["looking_for", "looking for", "seeking", "needs"],
  phone: ["phone", "phone number", "mobile", "tel"],
  linkedin: ["linkedin", "linkedin url", "linked in"],
};

/**
 * Count delimiter candidates in the first record, ignoring anything inside
 * quotes.
 *
 * Counting quoted content is how "Smith, Jr., Bob" in a semicolon file used to
 * elect the comma and shred every row. Quotes can be recognised without knowing
 * the delimiter yet, so this can run first.
 */
function detectDelimiter(text) {
  const counts = { "\t": 0, ",": 0, ";": 0 };
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') i += 1;
        else inQuotes = false;
      }
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
      continue;
    }
    if (ch === "\n") break;
    if (ch in counts) counts[ch] += 1;
  }
  const best = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
  return best[1] > 0 ? best[0] : ",";
}

/**
 * Split the whole text into records of cells, honouring RFC 4180 quoting.
 *
 * A spreadsheet quotes any field containing the delimiter, so "Doe, Jane" is
 * the ordinary case rather than an exotic one. Splitting on the delimiter
 * blindly turned that into name `"Doe` and company `Jane"` and reported no
 * error at all, which is the worst shape a bug can take: the import succeeds
 * and the data is wrong.
 *
 * Each record carries the source line it started on, so an error points at the
 * line the host sees in their spreadsheet even when earlier rows were blank or
 * a quoted field spanned several lines.
 */
function splitRecords(text, delim) {
  const records = [];
  let cells = [];
  let cur = "";
  let quoted = false; // this field was quoted, so do not trim its contents
  let inQuotes = false;
  let line = 1;
  let startLine = 1;

  const endField = () => {
    cells.push(quoted ? cur : cur.trim());
    cur = "";
    quoted = false;
  };
  const endRecord = () => {
    endField();
    if (!cells.every((c) => c === "")) records.push({ cells, line: startLine });
    cells = [];
  };

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];

    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          cur += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
        continue;
      }
      if (ch === "\n") line += 1;
      cur += ch;
      continue;
    }

    // A quote only opens a field at its start; a stray quote mid-value is data.
    if (ch === '"' && cur.trim() === "") {
      inQuotes = true;
      quoted = true;
      cur = "";
      continue;
    }
    if (ch === delim) {
      endField();
      continue;
    }
    if (ch === "\r") continue;
    if (ch === "\n") {
      endRecord();
      line += 1;
      startLine = line;
      continue;
    }
    cur += ch;
  }
  endRecord();
  return records;
}

function mapHeader(h) {
  const k = h.trim().toLowerCase();
  for (const [field, aliases] of Object.entries(HEADER_ALIASES)) {
    if (aliases.includes(k)) return field;
  }
  return KNOWN_FIELDS.includes(k) ? k : null;
}

/**
 * Pull an address out of free text such as "Jane Doe <jane@example.com>".
 *
 * The local part accepts anything legal but stops at the characters that wrap
 * an address rather than belong to it. Allowing everything except whitespace
 * swallows the leading `<` and yields `<jane@example.com`.
 */
function extractEmail(value) {
  const m = value.match(/[^\s@<>,;:"()[\]]+@[\w-]+(?:\.[\w-]+)+/);
  return m ? m[0] : null;
}

/**
 * Reject only what is clearly not an address.
 *
 * Deliberately permissive. The server's EmailStr is the real authority, and a
 * strict pattern here would drop legal-but-unusual local parts like
 * `o'brien@` — silently skipping a genuine guest, which is worse than
 * forwarding a doubtful address to the server that can judge it properly.
 *
 * What this does catch is a spreadsheet cell that is not an address at all.
 * That matters because the server validates the whole list in one pass, so a
 * single bad cell rejects every good row with it and the host is told nothing
 * about which line to fix.
 */
export function isLikelyEmail(value) {
  const s = String(value ?? "").trim();
  if (s === "" || /\s/.test(s)) return false;
  const at = s.indexOf("@");
  if (at < 1) return false;
  if (s.indexOf("@", at + 1) !== -1) return false;
  const domain = s.slice(at + 1);
  return /^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$/.test(domain);
}

const EVENT_NAME_ALIASES = ["event name", "event", "event title"];

/**
 * The event's own name, when the file carries it and every row agrees.
 *
 * An Eventbrite export has an Event Name column, which means a host who
 * uploads their roster has already told us what the event is called. Asking
 * them to retype it would be asking for something we are holding.
 *
 * Returns "" when the column is absent, empty, or disagrees between rows,
 * because a wrong prefilled name is worse than an empty box.
 */
export function suggestEventName(text) {
  if (String(text ?? "").trim() === "") return "";
  const delim = detectDelimiter(text);
  const records = splitRecords(text, delim);
  if (records.length < 2) return "";
  if (records[0].cells.some((c) => c.includes("@"))) return ""; // no header row
  const idx = records[0].cells.findIndex((h) =>
    EVENT_NAME_ALIASES.includes(h.trim().toLowerCase())
  );
  if (idx === -1) return "";
  const values = records
    .slice(1)
    .map((r) => (r.cells[idx] || "").trim())
    .filter(Boolean);
  if (values.length === 0) return "";
  return values.every((v) => v === values[0]) ? values[0] : "";
}

export function parsePaste(text) {
  if (String(text ?? "").trim() === "") return { rows: [], errors: [] };

  const delim = detectDelimiter(text);
  const records = splitRecords(text, delim);
  if (records.length === 0) return { rows: [], errors: [] };

  const firstHasEmail = records[0].cells.some((c) => c.includes("@"));
  let headers = null;
  let body = records;
  if (!firstHasEmail) {
    headers = records[0].cells.map(mapHeader);
    body = records.slice(1);
  }

  // A file with no address anywhere cannot be imported at all, and saying that
  // once is more use than repeating "No email found" on every line. Meetup is
  // the case this exists for: its attendee export carries names, RSVP status
  // and member titles, but no email addresses, so there is nobody to invite.
  if (
    headers &&
    !headers.includes("email") &&
    !body.some(({ cells }) => cells.some((c) => c.includes("@")))
  ) {
    return {
      rows: [],
      errors: [
        {
          line: 1,
          reason:
            "This file has no email column. Meetup exports do not include " +
            "attendee email addresses, so nobody can be invited from one. " +
            "Export from Eventbrite instead, or add an email column to your " +
            "own spreadsheet.",
        },
      ],
    };
  }

  const rows = [];
  const errors = [];

  body.forEach(({ cells, line }) => {
    const row = {};
    if (headers) {
      headers.forEach((h, i) => {
        if (h && cells[i]) row[h] = cells[i];
      });
      if (!row.email && cells[0]) {
        const e = extractEmail(cells[0]);
        if (e) row.email = e;
      }
      // Join a split name into the single field the product stores. A real
      // `name` column wins if the file somehow carries both.
      if (!row.name) {
        const joinedName = [row.first_name, row.last_name]
          .filter(Boolean)
          .join(" ")
          .trim();
        if (joinedName) row.name = joinedName;
      }
      delete row.first_name;
      delete row.last_name;
    } else {
      // No header — first column with @ is email; if "Name <email>" extract both.
      const joined = cells.join(" ");
      const email = extractEmail(joined);
      if (email) row.email = email;
      const nameCandidate = joined
        .replace(email || "", "")
        .replace(/[<>]/g, "")
        .trim();
      if (nameCandidate) row.name = nameCandidate;
    }

    if (!row.email) {
      errors.push({ line, reason: "No email found" });
      return;
    }
    if (!isLikelyEmail(row.email)) {
      errors.push({
        line,
        reason: `"${row.email}" is not a valid email address`,
      });
      return;
    }
    // Phone numbers out of a spreadsheet are the likeliest to be malformed.
    // A number that is already ten digits is reformatted silently; anything
    // else drops the whole row, named, rather than importing a contact whose
    // number looks fine and does not work. The server enforces this too.
    if (row.phone && !isValidPhone(row.phone)) {
      errors.push({
        line,
        reason: `Phone "${row.phone}" is not 10 digits`,
      });
      return;
    }
    if (row.phone) row.phone = formatPhone(row.phone);
    rows.push(row);
  });

  return { rows, errors };
}
