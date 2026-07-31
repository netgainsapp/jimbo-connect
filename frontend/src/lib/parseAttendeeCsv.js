/**
 * Parse a pasted or uploaded guest list into import rows.
 *
 * Extracted from BulkImportModal so the admin importer and the host importer
 * read spreadsheets identically. Two parsers would drift, and the drift would
 * show up as "the same file works for Jim and not for a customer".
 *
 * Handles tab, comma and semicolon delimiters, a header row or none, and
 * "Name <email@host>" in a single column. Bad rows are returned as errors with
 * their line number rather than silently dropped.
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

const HEADER_ALIASES = {
  email: ["email", "e-mail", "mail", "email address"],
  name: ["name", "full name", "fullname", "full_name"],
  role: ["role", "title", "position", "job title", "jobtitle"],
  company: ["company", "organization", "org", "employer"],
  industry: ["industry", "sector"],
  bio: ["bio", "about"],
  looking_for: ["looking_for", "looking for", "seeking", "needs"],
  phone: ["phone", "phone number", "mobile", "tel"],
  linkedin: ["linkedin", "linkedin url", "linked in"],
};

function detectDelimiter(line) {
  const counts = {
    "\t": (line.match(/\t/g) || []).length,
    ",": (line.match(/,/g) || []).length,
    ";": (line.match(/;/g) || []).length,
  };
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return sorted[0][1] > 0 ? sorted[0][0] : ",";
}

function mapHeader(h) {
  const k = h.trim().toLowerCase();
  for (const [field, aliases] of Object.entries(HEADER_ALIASES)) {
    if (aliases.includes(k)) return field;
  }
  return KNOWN_FIELDS.includes(k) ? k : null;
}

function extractEmail(value) {
  const m = value.match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/);
  return m ? m[0] : null;
}

export function parsePaste(text) {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length === 0) return { rows: [], errors: [] };

  const delim = detectDelimiter(lines[0]);
  const firstCells = lines[0].split(delim).map((s) => s.trim());
  const firstHasEmail = firstCells.some((c) => c.includes("@"));

  let headers = null;
  let body = lines;
  if (!firstHasEmail) {
    headers = firstCells.map(mapHeader);
    body = lines.slice(1);
  }

  const rows = [];
  const errors = [];

  body.forEach((line, idx) => {
    const cells = line.split(delim).map((s) => s.trim());
    const row = {};
    if (headers) {
      headers.forEach((h, i) => {
        if (h && cells[i]) row[h] = cells[i];
      });
      if (!row.email && cells[0]) {
        const e = extractEmail(cells[0]);
        if (e) row.email = e;
      }
    } else {
      // No header — first column with @ is email; if "Name <email>" extract both.
      const joined = cells.join(" ");
      const email = extractEmail(joined);
      if (email) row.email = email;
      const nameCandidate = cells
        .join(" ")
        .replace(email || "", "")
        .replace(/[<>]/g, "")
        .trim();
      if (nameCandidate) row.name = nameCandidate;
    }
    if (!row.email) {
      errors.push({ line: idx + (headers ? 2 : 1), reason: "No email found" });
      return;
    }
    // Phone numbers out of a spreadsheet are the likeliest to be malformed.
    // A number that is already ten digits is reformatted silently; anything
    // else drops the whole row, named, rather than importing a contact whose
    // number looks fine and does not work. The server enforces this too.
    if (row.phone && !isValidPhone(row.phone)) {
      errors.push({
        line: idx + (headers ? 2 : 1),
        reason: `Phone "${row.phone}" is not 10 digits`,
      });
      return;
    }
    if (row.phone) row.phone = formatPhone(row.phone);
    rows.push(row);
  });

  return { rows, errors };
}
