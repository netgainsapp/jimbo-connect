import { useEffect, useMemo, useRef, useState } from "react";
import {
  Upload,
  Users,
  AlertCircle,
  Copy,
  CheckCircle2,
  UserCheck,
  UserPlus,
} from "lucide-react";
import Modal from "./Modal.jsx";
import Avatar from "./Avatar.jsx";
import { adminApi, eventsApi } from "../lib/api.js";
import { copyToClipboard } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";

const KNOWN_FIELDS = [
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

function parsePaste(text) {
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
    } else {
      rows.push(row);
    }
  });

  return { rows, errors };
}

export default function BulkImportModal({
  open,
  onClose,
  onComplete,
  defaultEventId = "",
}) {
  const [text, setText] = useState("");
  const [eventId, setEventId] = useState("");
  const [defaultPassword, setDefaultPassword] = useState("");
  const [events, setEvents] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [existing, setExisting] = useState({}); // email -> match
  const [checking, setChecking] = useState(false);
  const fileRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    setText("");
    setEventId(defaultEventId || "");
    setDefaultPassword("");
    setResult(null);
    setExisting({});
    eventsApi
      .list()
      .then(setEvents)
      .catch(() => setEvents([]));
  }, [open, defaultEventId]);

  const parsed = useMemo(() => parsePaste(text), [text]);

  useEffect(() => {
    const emails = parsed.rows.map((r) => r.email.toLowerCase());
    if (emails.length === 0) {
      setExisting({});
      return;
    }
    const handle = setTimeout(async () => {
      setChecking(true);
      try {
        const res = await adminApi.checkEmails(emails);
        const map = {};
        (res.matches || []).forEach((m) => {
          map[m.email] = m;
        });
        setExisting(map);
      } catch {
        // ignore
      } finally {
        setChecking(false);
      }
    }, 350);
    return () => clearTimeout(handle);
  }, [parsed]);

  const newCount = parsed.rows.filter(
    (r) => !existing[r.email.toLowerCase()]
  ).length;
  const existingCount = parsed.rows.length - newCount;

  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result || ""));
    reader.readAsText(f);
  };

  const submit = async () => {
    if (parsed.rows.length === 0) {
      toast.show("Nothing to import", "error");
      return;
    }
    setSubmitting(true);
    try {
      const res = await adminApi.bulkImport(
        parsed.rows,
        eventId || null,
        defaultPassword || null
      );
      setResult(res);
      toast.show(
        `Imported ${res.created} new, ${res.skipped} existing${
          res.added_to_event ? `, added ${res.added_to_event} to event` : ""
        }`
      );
      onComplete?.();
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const copyAccounts = async () => {
    if (!result?.accounts?.length) return;
    const txt = result.accounts
      .map((a) => `${a.email}\t${a.password}`)
      .join("\n");
    await copyToClipboard(txt);
    toast.show("Accounts copied (tab-separated)");
  };

  return (
    <Modal open={open} onClose={onClose} maxWidth="max-w-2xl">
      <div className="p-6">
        <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
          <Users className="w-5 h-5 text-primary" /> Import attendees
        </h2>
        <p className="text-sm text-text-secondary mt-1">
          Paste a list of emails (one per line), or a CSV/TSV with headers like{" "}
          <code className="bg-bg-secondary px-1 rounded text-xs">
            email, name, company, role
          </code>
          . First row may be headers or skipped.
        </p>

        {!result && (
          <>
            <div className="mt-4 flex items-center gap-2">
              <button
                type="button"
                className="btn-outline"
                onClick={() => fileRef.current?.click()}
              >
                <Upload className="w-4 h-4" /> Upload CSV
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.tsv,.txt,text/*"
                className="hidden"
                onChange={onFile}
              />
              <span className="text-xs text-text-muted">or paste below</span>
            </div>

            <textarea
              className="input mt-3 min-h-[180px] font-mono text-xs"
              placeholder={`email,name,company,role
ava@example.com,Ava Reynolds,Trailhead Labs,Founder
ben@example.com,Ben Carter,Summit Robotics,VP Engineering

— or simply —

ava@example.com
ben@example.com`}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              <div>
                <label className="label">Add to event (optional)</label>
                <select
                  className="input"
                  value={eventId}
                  onChange={(e) => setEventId(e.target.value)}
                >
                  <option value="">— none —</option>
                  {events.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      {ev.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Default password (optional)</label>
                <input
                  className="input"
                  placeholder="leave blank to auto-generate"
                  value={defaultPassword}
                  onChange={(e) => setDefaultPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
              {parsed.rows.length > 0 ? (
                <>
                  <span className="text-text-primary font-semibold">
                    {parsed.rows.length} ready
                  </span>
                  {existingCount > 0 && (
                    <span className="inline-flex items-center gap-1 text-primary font-semibold">
                      <UserCheck className="w-3.5 h-3.5" />
                      {existingCount} existing
                    </span>
                  )}
                  {newCount > 0 && (
                    <span className="inline-flex items-center gap-1 text-text-secondary">
                      <UserPlus className="w-3.5 h-3.5" />
                      {newCount} new account{newCount === 1 ? "" : "s"}
                    </span>
                  )}
                  {checking && (
                    <span className="text-text-muted text-xs">checking…</span>
                  )}
                </>
              ) : (
                <span className="text-text-secondary">Nothing parsed yet.</span>
              )}
              {parsed.errors.length > 0 && (
                <span className="text-red-600 inline-flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {parsed.errors.length} skipped (no email)
                </span>
              )}
            </div>

            {parsed.rows.length > 0 && (
              <div className="mt-3 max-h-72 overflow-y-auto border border-border-default rounded-card divide-y divide-border-default">
                {parsed.rows.slice(0, 50).map((r, i) => {
                  const match = existing[r.email.toLowerCase()];
                  const p = match?.profile || {};
                  const displayName = match
                    ? p.name || match.email
                    : r.name || r.email;
                  const sub = match
                    ? [p.role, p.company].filter(Boolean).join(" · ")
                    : [r.role, r.company].filter(Boolean).join(" · ");
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-3 px-3 py-2"
                    >
                      <Avatar
                        name={displayName}
                        photoUrl={p.photo_url}
                        size={32}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-text-primary truncate">
                          {displayName}
                        </div>
                        <div className="text-xs text-text-secondary truncate">
                          {r.email}
                          {sub ? ` — ${sub}` : ""}
                        </div>
                      </div>
                      {match ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded-pill shrink-0">
                          <UserCheck className="w-3 h-3" /> Existing
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-text-secondary bg-bg-secondary px-2 py-0.5 rounded-pill shrink-0">
                          <UserPlus className="w-3 h-3" /> New
                        </span>
                      )}
                    </div>
                  );
                })}
                {parsed.rows.length > 50 && (
                  <div className="text-text-muted text-center py-2 text-xs">
                    + {parsed.rows.length - 50} more…
                  </div>
                )}
              </div>
            )}

            <div className="flex justify-end gap-2 mt-5">
              <button type="button" className="btn-ghost" onClick={onClose}>
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={submit}
                disabled={submitting || parsed.rows.length === 0}
              >
                {submitting
                  ? "Importing…"
                  : `Import ${parsed.rows.length || ""}`.trim()}
              </button>
            </div>
          </>
        )}

        {result && (
          <div className="mt-5">
            <div className="flex items-center gap-2 text-text-primary font-bold">
              <CheckCircle2 className="w-5 h-5 text-primary" /> Import complete
            </div>
            <div className="grid grid-cols-3 gap-3 mt-3">
              <Stat label="Created" value={result.created} />
              <Stat label="Already existed" value={result.skipped} />
              <Stat label="Added to event" value={result.added_to_event} />
            </div>

            {result.accounts?.length > 0 && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="label mb-0">New account credentials</div>
                  <button
                    type="button"
                    onClick={copyAccounts}
                    className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1"
                  >
                    <Copy className="w-3.5 h-3.5" /> Copy all
                  </button>
                </div>
                <div className="max-h-48 overflow-y-auto border border-border-default rounded-card text-xs">
                  <table className="w-full font-mono">
                    <thead className="bg-bg-secondary text-text-secondary font-sans">
                      <tr>
                        <th className="text-left px-2 py-1">Email</th>
                        <th className="text-left px-2 py-1">Temp password</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.accounts.map((a, i) => (
                        <tr key={i} className="border-t border-border-default">
                          <td className="px-2 py-1">{a.email}</td>
                          <td className="px-2 py-1">{a.password}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-text-muted mt-2">
                  Copy these now and share with attendees — they won't be shown again.
                </p>
              </div>
            )}

            {result.errors?.length > 0 && (
              <div className="mt-4">
                <div className="label">Errors</div>
                <ul className="text-xs text-red-600 list-disc pl-5">
                  {result.errors.map((e, i) => (
                    <li key={i}>
                      {e.email || "(no email)"} — {e.error}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex justify-end gap-2 mt-5">
              <button type="button" className="btn-primary" onClick={onClose}>
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

function Stat({ label, value }) {
  return (
    <div className="bg-bg-secondary rounded-card p-3 text-center">
      <div className="text-2xl font-bold text-text-primary">{value}</div>
      <div className="text-xs text-text-secondary">{label}</div>
    </div>
  );
}
