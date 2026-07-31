import { useEffect, useMemo, useRef, useState } from "react";
import { Upload, Users, AlertCircle, CheckCircle2 } from "lucide-react";
import Modal from "./Modal.jsx";
import { eventsApi } from "../lib/api.js";
import { parsePaste } from "../lib/parseAttendeeCsv.js";
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
 */
export default function AttendeeImportModal({ open, onClose, eventId, onComplete }) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const fileRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    setText("");
    setResult(null);
  }, [open]);

  const parsed = useMemo(() => parsePaste(text), [text]);

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result || ""));
    reader.readAsText(file);
  };

  const submit = async () => {
    if (parsed.rows.length === 0) return;
    setSubmitting(true);
    try {
      const res = await eventsApi.importAttendees(eventId, parsed.rows);
      setResult(res);
      onComplete?.();
    } catch (err) {
      toast.show(err?.message || "Import failed", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} label="Import guest list">
      <div className="p-6">
        <h2 className="text-xl font-bold text-ink">Import your guest list</h2>
        <p className="mt-1 text-sm text-stone">
          Paste from a spreadsheet or upload a CSV. Export the attendee list
          from Eventbrite, Meetup, or wherever your guests came from. A header
          row is optional.
        </p>

        {!result && (
          <>
            <div className="mt-4 flex items-center gap-3">
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="inline-flex items-center gap-2 rounded-card border border-line px-3 py-2 text-sm font-semibold text-ink hover:bg-cream"
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
              <span className="text-xs text-stone">or paste below</span>
            </div>

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              placeholder={"email,name,company\nava@acme.co,Ava Reynolds,Acme"}
              className="mt-3 w-full rounded-card border border-line p-3 font-mono text-sm"
            />

            {text.trim() !== "" && (
              <div className="mt-3 space-y-2 text-sm">
                <p className="flex items-center gap-2 font-semibold text-ink">
                  <Users className="h-4 w-4" />
                  {parsed.rows.length} guest
                  {parsed.rows.length === 1 ? "" : "s"} ready to import
                </p>
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
                className="rounded-card px-4 py-2 text-sm font-semibold text-stone hover:bg-cream"
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
            <p className="flex items-center gap-2 font-semibold text-ink">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              {result.added_to_event} added to this event
            </p>
            <p className="text-stone">
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
