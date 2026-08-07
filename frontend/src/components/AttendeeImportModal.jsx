import { useEffect, useMemo, useRef, useState } from "react";
import { Upload, Users, AlertCircle, CheckCircle2, ChevronDown } from "lucide-react";
import Modal from "./Modal.jsx";
import { eventsApi } from "../lib/api.js";
import { analyzePaste, isIgnoredHeader } from "../lib/parseAttendeeCsv.js";
import { SOURCES, normalizeHeader } from "../lib/importSource.js";
import { useToast } from "../hooks/useToast.jsx";

/**
 * Host-facing guest list import.
 *
 * Deliberately smaller than BulkImportModal, which is the admin tool. A host
 * gets no event picker (the event is the one they are on) and no password
 * field: they are importing addresses they do not own, so being able to set or
 * read the password of the created accounts would be a login for someone
 * else's account. The server refuses both regardless of what is sent here.
 *
 * It also does not check which emails already exist. That endpoint is admin
 * only, and telling a host which addresses already have accounts would leak
 * the membership of the whole platform to anyone who can paste a list.
 *
 * The source buttons are a shortcut, not a mode. Whatever a host picks, the
 * file is still inspected and the detected source wins for anything that
 * changes how it is read, so an Audience Republic export imports correctly
 * even when someone clicks "CSV or Excel".
 */

/**
 * The import sources a host can pick, with a slot for each one's mark.
 *
 * `logo` points at a file this repository does not ship. Eventbrite and
 * Audience Republic logos are their trademarks, and vendoring a competitor's
 * or partner's asset without their brand terms is not ours to do on their
 * behalf. Drop the approved file at the path below and it appears; until then
 * `mark` renders instead, which identifies the source in text and is
 * sufficient. Nothing else needs to change either way.
 */
const SOURCE_CHOICES = [
  {
    key: SOURCES.AUDIENCE_REPUBLIC,
    label: "Audience Republic",
    logo: "/brand/audience-republic.svg",
    mark: "AR",
  },
  {
    key: SOURCES.EVENTBRITE,
    label: "Eventbrite",
    logo: "/brand/eventbrite.svg",
    mark: "EB",
  },
  { key: SOURCES.GENERIC_CSV, label: "CSV or Excel", mark: "CSV" },
  { key: "other", label: "Other", mark: "—" },
];

/**
 * A source's logo, or its initials when the file is not present.
 *
 * The image is hidden on error rather than left broken: a missing asset should
 * degrade to the monogram, not to a torn-image icon in the middle of the
 * import screen.
 */
function SourceMark({ choice, active }) {
  const [failed, setFailed] = useState(false);
  const showImage = choice.logo && !failed;
  return (
    <span
      className={
        "flex h-5 w-5 shrink-0 items-center justify-center overflow-hidden rounded-sm text-[10px] font-bold " +
        (active ? "bg-white/20 text-white" : "bg-bg-secondary text-text-muted")
      }
      aria-hidden="true"
    >
      {showImage ? (
        <img
          src={choice.logo}
          alt=""
          className="h-full w-full object-contain"
          onError={() => setFailed(true)}
        />
      ) : (
        choice.mark
      )}
    </span>
  );
}

const SOURCE_LABELS = {
  [SOURCES.AUDIENCE_REPUBLIC]: "Audience Republic",
  [SOURCES.EVENTBRITE]: "Eventbrite",
  [SOURCES.GENERIC_CSV]: "CSV",
  [SOURCES.UNKNOWN]: "Unrecognised file",
};

// What a column may be pointed at. first_name and last_name are offered
// because a file often splits the name and the host may need to say which is
// which; they are joined into `name` on the way through and never stored
// separately.
const MAPPABLE_FIELDS = [
  "email",
  "name",
  "first_name",
  "last_name",
  "role",
  "company",
  "industry",
  "bio",
  "looking_for",
  "phone",
  "linkedin",
];

// Kept generic on purpose: Audience Republic moves its buttons around, and
// instructions that name a menu item are wrong the week after they change it.
const AUDIENCE_REPUBLIC_STEPS = [
  "Open the audience or attendee list for your event in Audience Republic.",
  "Export the list as CSV.",
  "Return to Intro Connect and upload the file.",
  "Review the matched fields.",
  "Import your attendees.",
];

export default function AttendeeImportModal({ open, onClose, eventId, onComplete }) {
  const [text, setText] = useState("");
  const [filename, setFilename] = useState("");
  const [chosen, setChosen] = useState(SOURCES.GENERIC_CSV);
  const [overrides, setOverrides] = useState({});
  const [showHelp, setShowHelp] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const fileRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    setText("");
    setFilename("");
    setChosen(SOURCES.GENERIC_CSV);
    setOverrides({});
    setShowHelp(false);
    setResult(null);
  }, [open]);

  const parsed = useMemo(
    () => analyzePaste(text, filename, overrides),
    [text, filename, overrides],
  );

  /** What this column is currently going to, override or guess. */
  const fieldFor = (header) => {
    const hit = parsed.mapped.find((m) => m.header === header);
    return hit ? hit.field : "";
  };

  /** Empty string means the host switched the column off, which has to be
   *  recorded rather than deleted: with no entry we would guess again. */
  const setMapping = (header, field) =>
    setOverrides((prev) => ({
      ...prev,
      [normalizeHeader(header)]: field || null,
    }));

  // What the file actually is beats what was clicked. A host who picks the
  // wrong button should still get a correct import rather than a lecture.
  const effectiveSource =
    parsed.source === SOURCES.AUDIENCE_REPUBLIC ||
    parsed.source === SOURCES.EVENTBRITE
      ? parsed.source
      : chosen;

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFilename(file.name);
    // A different file has different columns, so corrections made against the
    // last one would silently misapply to this one.
    setOverrides({});
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result || ""));
    reader.readAsText(file);
  };

  const submit = async () => {
    if (parsed.rows.length === 0) return;
    setSubmitting(true);
    try {
      const res = await eventsApi.importAttendees(
        eventId,
        parsed.rows,
        effectiveSource,
      );
      setResult(res);
      onComplete?.();
    } catch (err) {
      toast.show(err?.message || "Import failed", "error");
    } finally {
      setSubmitting(false);
    }
  };

  // Only email is required. The rest are shown so a host building a list from
  // scratch knows what the directory can carry, rather than guessing and
  // re importing later.
  const downloadTemplate = () => {
    const csv = [
      "email,name,role,company,industry,phone,linkedin",
      "ava@example.com,Ava Reynolds,Founder,Trailhead Labs,Software,3035550101,linkedin.com/in/example",
      "ben@example.com,Ben Carter,VP Engineering,Summit Robotics,Hardware,,",
    ].join("\n");
    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv;charset=utf-8" })
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "intro-connect-guest-list-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const isAudienceRepublic = chosen === SOURCES.AUDIENCE_REPUBLIC;

  return (
    <Modal open={open} onClose={onClose} label="Import guest list">
      <div className="p-6">
        <h2 className="text-xl font-bold text-text-primary">
          {isAudienceRepublic
            ? "Import from Audience Republic"
            : "Import your guest list"}
        </h2>
        <p className="mt-1 text-sm text-text-muted">
          {isAudienceRepublic
            ? "Upload your attendee export and Intro Connect will match the fields automatically."
            : "Paste from a spreadsheet or upload a CSV. An Eventbrite or Audience Republic export works as is. A header row is optional, and a name split across first and last columns is joined for you."}
        </p>

        {!result && (
          <>
            <div className="mt-4 flex flex-wrap gap-2">
              {SOURCE_CHOICES.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => setChosen(s.key)}
                  className={
                    "inline-flex items-center gap-2 rounded-card border px-3 py-1.5 text-sm font-semibold " +
                    (chosen === s.key
                      ? "border-primary bg-primary text-white"
                      : "border-border-default text-text-primary hover:bg-bg-secondary")
                  }
                >
                  <SourceMark choice={s} active={chosen === s.key} />
                  {s.label}
                </button>
              ))}
            </div>

            {isAudienceRepublic && (
              <div className="mt-3 rounded-card bg-bg-secondary p-3 text-sm">
                <p className="text-text-primary">
                  Export the attendees for this event from Audience Republic,
                  then upload the file here. Intro Connect will automatically
                  match the fields.
                </p>
                <p className="mt-1 text-xs text-text-muted">
                  Your Audience Republic account and data remain unchanged.
                </p>
                <button
                  type="button"
                  onClick={() => setShowHelp((v) => !v)}
                  className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                >
                  <ChevronDown
                    className={
                      "h-3 w-3 transition-transform " + (showHelp ? "rotate-180" : "")
                    }
                  />
                  How to export from Audience Republic
                </button>
                {showHelp && (
                  <ol className="mt-2 list-inside list-decimal space-y-1 text-xs text-text-muted">
                    {AUDIENCE_REPUBLIC_STEPS.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                )}
              </div>
            )}

            <div className="mt-4 flex items-center gap-3">
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="inline-flex items-center gap-2 rounded-card border border-border-default px-3 py-2 text-sm font-semibold text-text-primary hover:bg-bg-secondary"
              >
                <Upload className="h-4 w-4" />
                Upload CSV
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.tsv,.txt,text/csv"
                onChange={onFile}
                className="hidden"
              />
              <span className="text-xs text-text-muted">or paste below</span>
              <button
                type="button"
                onClick={downloadTemplate}
                className="ml-auto text-xs font-semibold text-primary hover:underline"
              >
                Download a template
              </button>
            </div>

            <textarea
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setFilename("");
                setOverrides({});
              }}
              rows={8}
              placeholder={"email,name,company\nava@acme.co,Ava Reynolds,Acme"}
              className="mt-3 w-full rounded-card border border-border-default p-3 font-mono text-sm"
            />

            {text.trim() !== "" && (
              <div className="mt-3 space-y-3 text-sm">
                <p className="flex items-center gap-2 font-semibold text-text-primary">
                  <Users className="h-4 w-4" />
                  {parsed.rows.length} guest
                  {parsed.rows.length === 1 ? "" : "s"} ready to import
                </p>

                {parsed.headers.length > 0 && (
                  <div className="rounded-card border border-border-default p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Detected source
                    </p>
                    <p className="text-text-primary">
                      {SOURCE_LABELS[parsed.source] || "CSV"}
                    </p>

                    <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Mapped fields
                    </p>
                    {/* Editable, because automatic mapping is a good guess and
                        the host is the one looking at the file. Columns we
                        deliberately exclude are not listed here; they are
                        below, and switching them on is a separate decision. */}
                    <ul className="mt-1 space-y-1">
                      {parsed.headers
                        .filter((h) => h && h.trim() !== "" && !isIgnoredHeader(h))
                        .map((h) => (
                          <li key={h} className="flex items-center gap-2">
                            <span className="min-w-0 flex-1 truncate text-text-primary">
                              {h}
                            </span>
                            <span className="text-text-muted">→</span>
                            <select
                              value={fieldFor(h)}
                              onChange={(e) => setMapping(h, e.target.value)}
                              aria-label={`Import ${h} as`}
                              className="rounded-card border border-border-default bg-white px-2 py-1 text-sm text-text-primary"
                            >
                              <option value="">Do not import</option>
                              {MAPPABLE_FIELDS.map((f) => (
                                <option key={f} value={f}>
                                  {f.replace(/_/g, " ")}
                                </option>
                              ))}
                            </select>
                          </li>
                        ))}
                    </ul>

                    {parsed.unmapped.length > 0 && (
                      <>
                        <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-text-muted">
                          Not imported
                        </p>
                        <p className="text-text-muted">
                          {parsed.unmapped.join(", ")}
                        </p>
                      </>
                    )}

                    {parsed.ignored.length > 0 && (
                      /* Named explicitly rather than lumped in with "not
                         imported": a host should be able to see that we did
                         not quietly take marketing consent, date of birth or
                         gender from another company's CRM. */
                      <>
                        <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-text-muted">
                          Deliberately left out
                        </p>
                        <p className="text-text-muted">
                          {parsed.ignored.join(", ")}. Marketing consent and
                          personal details stay in Audience Republic.
                        </p>
                      </>
                    )}
                  </div>
                )}

                {parsed.errors.length > 0 && (
                  <div className="rounded-card bg-amber-50 p-3 text-amber-900">
                    <p className="flex items-center gap-2 font-semibold">
                      <AlertCircle className="h-4 w-4" />
                      {parsed.errors.length} row
                      {parsed.errors.length === 1 ? "" : "s"} will be skipped
                    </p>
                    <ul className="mt-1 list-inside list-disc">
                      {parsed.errors.slice(0, 8).map((e, i) => (
                        <li key={i}>
                          Line {e.line}: {e.reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-card px-4 py-2 text-sm font-semibold text-text-muted hover:bg-bg-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={submit}
                disabled={submitting || parsed.rows.length === 0}
                className="rounded-card bg-primary px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
              >
                {submitting
                  ? "Importing..."
                  : `Import ${parsed.rows.length || ""}`.trim()}
              </button>
            </div>
          </>
        )}

        {result && (
          <div className="mt-4 space-y-3 text-sm">
            <p className="flex items-center gap-2 font-semibold text-text-primary">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              {result.added_to_event} attendee
              {result.added_to_event === 1 ? " is" : "s are"} ready for Intro
              Connect
            </p>
            <p className="text-text-muted">
              {result.created} new account{result.created === 1 ? "" : "s"}{" "}
              created, {result.skipped} already had one. Everyone new gets an
              invitation email with their own sign-in link.
            </p>
            {result.errors?.length > 0 && (
              <div className="rounded-card bg-amber-50 p-3 text-amber-900">
                <p className="font-semibold">
                  {result.errors.length} not added
                </p>
                {/* Named per row rather than summarised: at the attendee cap
                    the host needs to know exactly who missed out. */}
                <ul className="mt-1 list-inside list-disc">
                  {result.errors.slice(0, 10).map((e, i) => (
                    <li key={i}>
                      {e.email}: {e.error}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="rounded-card bg-primary px-4 py-2 text-sm font-bold text-white"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
